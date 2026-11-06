"""Shape text through patched fonts with HarfBuzz and check what is drawn.

Run `scripts/build-samples.sh` first; it downloads two OFL fonts and patches them.
"""

import random
import string
import subprocess
from functools import cache
from pathlib import Path

import pytest
import uharfbuzz as hb

OUT = Path(__file__).resolve().parent.parent / "fonts" / "out"
MASKED = ["CascadiaCode-Masked.ttf", "SourceCodePro-Regular-Masked.otf"]
OPT_IN = {"CascadiaCode-MASK.ttf": "MASK", "SourceCodePro-Regular-MASK.otf": "MASK"}


@cache
def _font(name: str) -> hb.Font:
    path = OUT / name
    if not path.exists():
        pytest.fail(f"{path} missing: run scripts/build-samples.sh")
    return hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))


def shape(name: str, text: str, features: dict | None = None) -> list[str]:
    font = _font(name)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    return [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]


def render(name: str, text: str, features: dict | None = None) -> str:
    """`.` for a mask glyph, the character otherwise. Fonts here keep one glyph per char."""
    glyphs = shape(name, text, features)
    assert len(glyphs) == len(text), (text, glyphs)
    return "".join("•" if g.startswith("sm.mask.") else c for g, c in zip(glyphs, text))


CASES = [
    # (typed, drawn)
    ("ghp_Xk9QzR2mLp7vB4nT8wYc ok", "ghp_Xk9Q•••••••••••••••• ok"),
    ("ghp_abcdefgh", "ghp_abcd••••"),  # prefixes never use the word filter
    ("xghp_Xk9QzR2mLp7v", "xghp_Xk9QzR2mLp7v"),  # not at a word start
    ("github_pat_11ABCDEFG0_xyz", "github_pat_11AB••••••••••"),
    ("sk-ant-api03-Ab_cd-EfGh", "sk-ant-api0••••••••••••"),
    ("AKIAIOSFODNN7EXAMPLE", "AKIAIOSF••••••••••••"),
    ("AKIAIOSFODNN7EXAMPLE.", "AKIAIOSF••••••••••••."),  # ends at the first non-key char
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIi", "eyJhbGc••••••••••••••••••••••"),  # .eyJ can't restart it
    ("TOKEN=ghp_Xk9QzR2mLp7v", "TOKEN=ghp_Xk9Q••••••••"),
    ("GITHUB_TOKEN=Abcd1234zzzz", "GITHUB_TOKEN=Abcd••••••••"),
    ("export API_KEY='Abcd1234zz'", "export API_KEY='Abcd••••••'"),
    ("PASSWORD=hunter22", "PASSWORD=hunt••••"),  # passwords skip the word filter
    ('{"password": "s3cretPass"}', '{"password": "s3cr••••••"}'),
    # VS Code renders some spaces as U+00A0
    ('{"password":\u00a0"s3cretPass"}', '{"password":\u00a0"s3cr••••••"}'),
    ("Authorization: Bearer abc1EFGHijkl", "Authorization: Bearer abc1••••••••"),
    ("Authorization:\u00a0Bearer\u00a0abc1EFGHijkl", "Authorization:\u00a0Bearer\u00a0abc1••••••••"),
    ("curl --token Abc12345 -v", "curl --token Abc1•••• -v"),
    ("MYTOKEN=Abcd1234zzzz", "MYTOKEN=Abcd1234zzzz"),
    ("MONKEY=banana", "MONKEY=banana"),
    ("token: string", "token: string"),  # word filter
    ("TOKEN=abcdefgh", "TOKEN=abcdefgh"),  # word filter: lowercase window reads as a word
    ("TOKEN=abc", "TOKEN=abc"),  # never masks inside the kept window
    ("ghp_Xk9", "ghp_Xk9"),
    ("plain text, no secrets", "plain text, no secrets"),
]


@pytest.mark.parametrize("name", MASKED)
@pytest.mark.parametrize(("typed", "drawn"), CASES)
def test_cases(name, typed, drawn):
    assert render(name, typed) == drawn


@pytest.mark.parametrize("name", MASKED)
def test_typing_never_redraws(name):
    """Every prefix of a line draws exactly as that prefix of the whole line: once a
    character is drawn, more text arriving after it never changes it."""
    rng = random.Random(3310)
    alphabet = string.ascii_letters + string.digits + "_-=:.\"' "
    seeds = [t for t, _ in CASES]
    lines = seeds + [
        rng.choice(seeds)[: rng.randrange(1, 14)] + "".join(rng.choices(alphabet, k=rng.randrange(1, 40)))
        for _ in range(300)
    ]
    for line in lines:
        whole = render(name, line)
        for i in range(1, len(line)):
            # Compare what masking draws, not glyph names: the font's own ligatures (Cascadia's
            # --) use lookahead and may legitimately redraw.
            assert render(name, line[:i]) == whole[:i], (line, i)


@pytest.mark.parametrize(("name", "tag"), OPT_IN.items())
def test_opt_in_build_masks_only_with_its_feature(name, tag):
    assert render(name, "ghp_Xk9QzR2mLp7v") == "ghp_Xk9QzR2mLp7v"
    assert render(name, "ghp_Xk9QzR2mLp7v", {tag: True}) == "ghp_Xk9Q••••••••"


SOURCES = {
    "CascadiaCode-Masked.ttf": "CascadiaCode.ttf",
    "CascadiaCode-MASK.ttf": "CascadiaCode.ttf",
    "SourceCodePro-Regular-Masked.otf": "SourceCodePro-Regular.otf",
    "SourceCodePro-Regular-MASK.otf": "SourceCodePro-Regular.otf",
}
PLAIN = [
    "a == b -> c != d <= e >>= f |> g :: h ... i // j /* k */ www &&",
    "fi fl 0O 1lI {[()]} 0x1F 1/2 3rd 2^10 ~/.config",
    'const user = { name: "Ada", sort_key: "modified_date" };',
]


@pytest.mark.parametrize("name", [*MASKED, *OPT_IN])
def test_text_without_secrets_shapes_as_the_original(name):
    """Every feature the original font has, alone, shapes plain code identically."""
    from fontTools.ttLib import TTFont

    src = OUT.parent / "in" / SOURCES[name]
    tags = sorted({r.FeatureTag for r in TTFont(src)["GSUB"].table.FeatureList.FeatureRecord})
    original = hb.Font(hb.Face(hb.Blob.from_file_path(str(src))))
    for tag in [None, *tags]:
        features = {tag: True} if tag else {}
        for text in PLAIN:
            buf = hb.Buffer()
            buf.add_str(text)
            buf.guess_segment_properties()
            hb.shape(original, buf, features)
            expected = [original.glyph_to_string(i.codepoint) for i in buf.glyph_infos]
            assert shape(name, text, features) == expected, (tag, text)


@pytest.mark.parametrize("name", [*MASKED, *OPT_IN])
def test_passes_ots_sanitizer(name, tmp_path):
    import ots

    result = ots.sanitize(str(OUT / name), str(tmp_path / name), capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize("name", MASKED)
def test_mask_dot_has_cell_width(name):
    font = _font(name)
    width = font.get_glyph_h_advance(font.get_nominal_glyph(ord("0")))
    mask = font.get_glyph_from_name("sm.mask.alnum")
    assert font.get_glyph_h_advance(mask) == width
