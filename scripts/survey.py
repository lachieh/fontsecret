"""Patch every font in a directory and check masking on each one.

    uv run python scripts/survey.py fonts/nf-src docs/nerd-fonts-survey.md

Per font: outline format, which stylistic sets it already uses, whether patching works,
whether the masking cases draw as expected (always-on and opt-in MASK builds), whether typing ever redraws,
whether plain code still shapes as in the original under each of its features, whether
`fontsecret verify` passes, and OTS.
"""

import io
import random
import string
import sys
from pathlib import Path

import ots
import uharfbuzz as hb
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from fontsecret import font as patcher  # noqa: E402
from fontsecret.patterns import load  # noqa: E402
from fontsecret.verify import verify  # noqa: E402
from test_masking import CASES, PLAIN  # noqa: E402

PATTERNS = load()


def hbfont(data: bytes) -> hb.Font:
    return hb.Font(hb.Face(hb.Blob(data)))


def glyph_ids(font: hb.Font, text: str, features: dict) -> list[tuple[int, int]]:
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features)
    return [(i.codepoint, i.cluster) for i in buf.glyph_infos]


def render(font: hb.Font, masks: set[int], text: str) -> str:
    """• for each character whose cluster contains a mask glyph. Clusters, not glyphs,
    so fonts whose ligatures merge characters are still compared per character."""
    glyphs = glyph_ids(font, text, {})
    starts = sorted({c for _, c in glyphs})
    masked = {c for g, c in glyphs if g in masks}
    out = []
    for i, ch in enumerate(text):
        cluster = max(s for s in starts if s <= i)
        out.append("•" if cluster in masked else ch)
    return "".join(out)


def survey(path: Path) -> dict:
    row: dict = {"font": path.name.split("--")[0], "file": path.name.split("--", 1)[1]}
    original = TTFont(path)
    row["outlines"] = ("CFF2" if "CFF2" in original else "CFF" if "CFF " in original else "glyf") + (
        " var" if "fvar" in original else "")
    gsub = original["GSUB"].table if "GSUB" in original else None
    records = gsub.FeatureList.FeatureRecord if gsub and gsub.FeatureList else []
    tags = sorted({r.FeatureTag for r in records})
    row["ss_used"] = [t for t in tags if t.startswith("ss") and t[2:].isdigit()]
    row["ligatures"] = any(t in tags for t in ("calt", "liga", "dlig"))

    font = TTFont(path)
    try:
        report = patcher.patch(font, PATTERNS, patcher.ALWAYS_ON)
        order = font.getGlyphOrder()
        buf = io.BytesIO()
        font.save(buf)
    except Exception as e:  # noqa: BLE001 - the survey records every failure
        row["error"] = f"{type(e).__name__}: {e}"[:120]
        return row
    row["skipped"] = report["skipped"]
    masks = {i for i, g in enumerate(order) if g.startswith("sm.mask.")}
    data = buf.getvalue()
    patched, plain = hbfont(data), hbfont(path.read_bytes())

    opt_in = TTFont(path)
    try:
        patcher.patch(opt_in, PATTERNS)
        opt_in_data = io.BytesIO()
        opt_in.save(opt_in_data)
        optional = hbfont(opt_in_data.getvalue())
        row["opt_in_failures"] = [
            text for text, _ in CASES
            if glyph_ids(optional, text, {}) != glyph_ids(plain, text, {})
            or glyph_ids(optional, text, {patcher.DEFAULT_FEATURE: True})
            != glyph_ids(patched, text, {})
        ]
    except Exception as e:  # noqa: BLE001 - the survey records every failure
        row["opt_in_failures"] = [f"{type(e).__name__}: {e}"[:120]]

    row["case_failures"] = [t for t, want in CASES if render(patched, masks, t) != want]

    rng = random.Random(3310)
    seeds = [t for t, _ in CASES]
    alphabet = string.ascii_letters + string.digits + "_-=:.\"' "
    lines = seeds + [rng.choice(seeds)[: rng.randrange(1, 14)]
                     + "".join(rng.choices(alphabet, k=rng.randrange(1, 40))) for _ in range(150)]
    redraws = 0
    for line in lines:
        whole = render(patched, masks, line)
        redraws += any(render(patched, masks, line[:i]) != whole[:i] for i in range(1, len(line)))
    row["redraws"] = redraws

    changed = []
    for tag in [None, *tags]:
        feats = {tag: True} if tag else {}
        for text in PLAIN:
            if [g for g, _ in glyph_ids(patched, text, feats)] != [g for g, _ in glyph_ids(plain, text, feats)]:
                changed.append(tag or "default")
                break
    row["plain_changed"] = changed

    row["ots"] = sanitize(data)
    row["verify"] = verify(TTFont(path), TTFont(io.BytesIO(data))).errors
    row["ots_original"] = sanitize(path.read_bytes())
    return row


def sanitize(data: bytes) -> str:
    tmp = Path("/tmp/survey-ots")
    tmp.mkdir(exist_ok=True)
    (tmp / "in.bin").write_bytes(data)
    r = ots.sanitize(str(tmp / "in.bin"), str(tmp / "out.bin"), capture_output=True)
    return "ok" if r.returncode == 0 else (r.stderr.decode().strip().splitlines() or ["failed"])[-1][:80]


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for path in sorted(src.iterdir(), key=lambda p: p.name.lower()):
        if path.suffix.lower() in (".ttf", ".otf"):
            rows.append(survey(path))
            r = rows[-1]
            print(r["font"], r.get("error") or f"cases={r['case_failures']} redraws={r['redraws']} "
                  f"opt-in={r['opt_in_failures']} plain={r['plain_changed']} ots={r['ots']}/{r['ots_original']} skipped={len(r['skipped'])}", flush=True)

    lines = [
        "| Font | Outlines | ss in use | Ligatures | Result | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        ss = " ".join(r["ss_used"]) or "—"
        if "error" in r:
            result, notes = "❌ patch fails", r["error"]
        else:
            problems = []
            if r["case_failures"]:
                problems.append(f"{len(r['case_failures'])} cases differ: "
                                + ", ".join(f"`{c}`" for c in r["case_failures"][:3]))
            if r["opt_in_failures"]:
                problems.append("opt-in MASK: " + "; ".join(r["opt_in_failures"][:3]))
            if r["redraws"]:
                problems.append(f"{r['redraws']} lines redraw")
            if r["plain_changed"]:
                problems.append("plain code changes under " + ", ".join(r["plain_changed"]))
            if r["verify"]:
                problems.append("verify: " + "; ".join(r["verify"][:2]))
            if r["ots"] != "ok" and r["ots_original"] == "ok":
                problems.append("OTS: " + r["ots"])
            elif r["ots"] != "ok":
                problems.append("OTS fails on the original too")
            if r["skipped"]:
                problems.append(f"{len(r['skipped'])} triggers skipped (missing glyphs)")
            result = "✅" if not problems else "⚠️"
            notes = "; ".join(problems)
        lig = "yes" if r["ligatures"] else ""
        lines.append(f"| {r['font']} | {r['outlines']} | {ss} | {lig} | {result} | {notes} |")
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
