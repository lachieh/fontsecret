"""`fontsecret verify` passes real builds and fails fonts tampered with after patching.

Each tampering is something a hostile font could do to make the screen disagree with the
text. Run `scripts/build-samples.sh` first.
"""

from pathlib import Path

import pytest
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from fontsecret.verify import verify

FONTS = Path(__file__).resolve().parent.parent / "fonts"
BUILDS = {
    "CascadiaCode-Masked.ttf": "CascadiaCode.ttf",
    "CascadiaCode-SM.ttf": "CascadiaCode.ttf",
    "SourceCodePro-Regular-Masked.otf": "SourceCodePro-Regular.otf",
    "SourceCodePro-Regular-SM.otf": "SourceCodePro-Regular.otf",
}
TAMPER_ON = ["CascadiaCode-Masked.ttf", "SourceCodePro-Regular-Masked.otf"]


def load(name: str, folder: str) -> TTFont:
    path = FONTS / folder / name
    if not path.exists():
        pytest.fail(f"{path} missing: run scripts/build-samples.sh")
    return TTFont(path)


def roundtrip(font: TTFont, tmp_path: Path) -> TTFont:
    out = tmp_path / "tampered"
    font.save(out)
    return TTFont(out)


@pytest.mark.parametrize(("patched", "original"), BUILDS.items())
def test_real_builds_verify(patched, original):
    report = verify(load(original, "in"), load(patched, "out"))
    assert report.ok, report.errors


def _glyph_of(font: TTFont, ch: str) -> str:
    return font.getBestCmap()[ord(ch)]


def remap_character(font: TTFont, original: TTFont) -> None:
    """Draw every `l` as `s`: the phishing-kit trick."""
    for table in font["cmap"].tables:
        if ord("l") in table.cmap:
            table.cmap[ord("l")] = _glyph_of(font, "s")


def redraw_original_glyph(font: TTFont, original: TTFont) -> None:
    """Make `a` draw as `o` without touching cmap or GSUB."""
    a, o = _glyph_of(font, "a"), _glyph_of(font, "o")
    if "glyf" in font:
        font["glyf"][a] = font["glyf"][o]
        if "gvar" in font:  # keep the variation data's point count consistent
            font["gvar"].variations[a] = font["gvar"].variations[o]
    else:
        strings = font["CFF "].cff.topDictIndex[0].CharStrings
        strings.charStringsIndex[strings.charStrings[a]] = strings[o]


def disguise_marker(font: TTFont, original: TTFont) -> None:
    """Point a marker at a different original glyph's shape: `ghp_` would draw as `ghp-`."""
    marker = next(g for g in font.getGlyphOrder() if g.startswith("underscore.sm."))
    hyphen = _glyph_of(font, "-")
    if "glyf" in font:
        font["glyf"][marker] = font["glyf"][hyphen]
        if "gvar" in font:
            font["gvar"].variations[marker] = font["gvar"].variations[hyphen]
    else:
        strings = font["CFF "].cff.topDictIndex[0].CharStrings
        strings.charStringsIndex[strings.charStrings[marker]] = strings[hyphen]


def added_lookup_swaps_letters(font: TTFont, original: TTFont) -> None:
    """An added substitution that replaces `a` with the original `b`."""
    gsub = font["GSUB"].table
    for lookup in gsub.LookupList.Lookup[:5]:
        for st in lookup.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if hasattr(st, "mapping") and st.mapping:
                st.mapping[_glyph_of(font, "a")] = _glyph_of(font, "b")
                return
    raise AssertionError("no added single substitution found")


def change_original_lookup(font: TTFont, original: TTFont) -> None:
    """Edit one of the font's own lookups."""
    gsub = font["GSUB"].table
    shift = len(gsub.LookupList.Lookup) - len(original["GSUB"].table.LookupList.Lookup)
    for lookup in gsub.LookupList.Lookup[shift:]:
        for st in lookup.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if getattr(st, "mapping", None):
                key = next(iter(st.mapping))
                st.mapping[key] = _glyph_of(font, "x")
                return
    raise AssertionError("no original single substitution found")


def enable_hidden_feature(font: TTFont, original: TTFont) -> None:
    """Attach one of the font's opt-in lookups to an always-on feature."""
    gsub = font["GSUB"].table
    records = gsub.FeatureList.FeatureRecord
    optional = next(r for r in records if r.FeatureTag.startswith(("ss", "cv", "salt", "zero")))
    always = next(r for r in records if r.FeatureTag in ("ccmp", "calt", "locl"))
    always.Feature.LookupListIndex = always.Feature.LookupListIndex + optional.Feature.LookupListIndex


TAMPERINGS = {
    "remap_character": (remap_character, "cmap changed"),
    "redraw_original_glyph": (redraw_original_glyph, "original glyph outlines changed"),
    "disguise_marker": (disguise_marker, "draws differently"),
    "added_lookup_swaps_letters": (added_lookup_swaps_letters, "with original glyph"),
    "change_original_lookup": (change_original_lookup, "original lookup"),
    "enable_hidden_feature": (enable_hidden_feature, "features of"),
}


@pytest.mark.parametrize("name", TAMPER_ON)
@pytest.mark.parametrize("tamper", TAMPERINGS)
def test_tampering_fails(name, tamper, tmp_path):
    original = load(BUILDS[name], "in")
    font = load(name, "out")
    edit, expected = TAMPERINGS[tamper]
    edit(font, original)
    report = verify(original, roundtrip(font, tmp_path))
    assert not report.ok, f"{tamper} passed verify"
    assert any(expected in e for e in report.errors), report.errors
