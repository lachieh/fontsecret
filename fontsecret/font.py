"""Add secret masking to an existing OpenType font with fontTools.

The font keeps every existing glyph and lookup. The masking lookups are placed first in
the GSUB lookup list, so within their shaping stage they see the characters as typed,
before ligatures, contextual alternates or stylistic sets change them.
"""

import copy
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.misc.psCharStrings import T2CharString
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._g_l_y_f import Glyph

from . import fea
from .patterns import Patterns

ALWAYS_ON = "ccmp"


class Unsupported(Exception):
    pass


def patch(font: TTFont, patterns: Patterns, feature: str | None = None) -> dict:
    """Patch `font` in place. `feature` is a tag (ssNN, ccmp ...); None picks a free ssNN."""
    if "CFF2" in font:
        raise Unsupported("CFF2 (variable OTF) outlines are not supported; use the TTF build")
    if "glyf" not in font and "CFF " not in font:
        raise Unsupported("font has neither glyf nor CFF outlines")

    # Recalculating bounding boxes would re-encode every glyph. Keep the glyphs we don't
    # own byte for byte: some fonts (Iosevka) only pass OTS in their original encoding.
    font.recalcBBoxes = False
    gsub = _ensure_gsub(font)
    tag = feature or _free_stylistic_set(gsub)

    p = fea.plan(patterns, font.getBestCmap(), _rvrn_variants(gsub))
    _add_glyphs(font, p)
    ours = _build_lookups(font, p.fea)
    _prepend_lookups(font, ours, tag)
    # Device-pixel width caches list every glyph; they are optional, so drop them.
    for t in ("hdmx", "LTSH", "VDMX"):
        if t in font:
            del font[t]
    # cmap and OS/2 are only read. fontTools re-encodes any table it has loaded, which can
    # change bytes (OS/2.usFirstCharIndex), so drop the loaded copies and keep the originals.
    for t in ("cmap", "OS/2"):
        if font.reader is not None and t in font.reader:
            font.tables.pop(t, None)
    return {"feature": tag, "triggers": len(patterns.triggers) - len(p.skipped),
            "skipped": [t.text for t in p.skipped], "glyphs_added": len(p.markers) + len(p.masks)}


def rename(font: TTFont, suffix: str) -> None:
    """Append `suffix` to the family name, as OFL Reserved Font Names require for a modified font."""
    name = font["name"]
    family = name.getBestFamilyName()
    new_family = f"{family} {suffix}"
    ps_old, ps_new = family.replace(" ", ""), new_family.replace(" ", "")
    for rec in name.names:
        if rec.nameID in (1, 3, 4, 16, 18, 21):
            rec.string = rec.toUnicode().replace(family, new_family)
        elif rec.nameID in (6, 20, 25):
            rec.string = rec.toUnicode().replace(ps_old, ps_new)
    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [n.replace(ps_old, ps_new) for n in cff.fontNames]
        top = cff.topDictIndex[0]
        for key in ("FamilyName", "FullName"):
            if hasattr(top, key):
                setattr(top, key, getattr(top, key).replace(family, new_family))


def _free_stylistic_set(gsub) -> str:
    used = {r.FeatureTag for r in gsub.FeatureList.FeatureRecord} if gsub else set()
    for n in range(20, 0, -1):
        if (tag := f"ss{n:02d}") not in used:
            return tag
    raise Unsupported("all of ss01-ss20 are taken; pass a feature tag explicitly")


def _rvrn_variants(gsub) -> dict[str, set[str]]:
    """Glyphs `rvrn` may swap in. rvrn runs in a shaping stage before ours."""
    out: dict[str, set[str]] = {}
    if gsub is None:
        return out
    indices = {i for r in gsub.FeatureList.FeatureRecord if r.FeatureTag == "rvrn"
               for i in r.Feature.LookupListIndex}
    fv = getattr(gsub, "FeatureVariations", None)
    if fv:
        for rec in fv.FeatureVariationRecord:
            for sub in rec.FeatureTableSubstitution.SubstitutionRecord:
                if gsub.FeatureList.FeatureRecord[sub.FeatureIndex].FeatureTag == "rvrn":
                    indices |= set(sub.Feature.LookupListIndex)
    for i in indices:
        lookup = gsub.LookupList.Lookup[i]
        for st in lookup.SubTable:
            st = getattr(st, "ExtSubTable", st)
            for src, dst in getattr(st, "mapping", {}).items():
                out.setdefault(src, set()).add(dst)
    return out


# --- glyphs ---------------------------------------------------------------------------

def _add_glyphs(font: TTFont, p: fea.Plan) -> None:
    # These tables decompile against the glyph count; load them before it grows. Other
    # tables stay raw and are written back untouched (fontTools can't parse every one:
    # ProFont's AAT morx).
    for tag in ("glyf", "loca", "gvar", "hmtx", "vmtx", "HVAR", "VVAR", "CFF ", "post", "GSUB"):
        if tag in font:
            font[tag]
    order = font.getGlyphOrder()
    existing = set(order)
    clash = [g for g in [*p.markers, *p.masks] if g in existing]
    if clash:
        raise Unsupported(f"font already has glyphs named {clash[:3]}; already patched?")
    font.setGlyphOrder(order + list(p.markers) + list(p.masks))
    hmtx = font["hmtx"]
    advance = hmtx[font.getBestCmap()[ord("0")]][0]
    if "glyf" in font:
        _add_glyf(font, p, advance)
    else:
        _add_cff(font, p, advance)
    for marker, base in p.markers.items():
        hmtx[marker] = hmtx[base]
    if "vmtx" in font:  # vertical metrics list every glyph too
        vmtx, zero = font["vmtx"], font.getBestCmap()[ord("0")]
        for marker, base in p.markers.items():
            vmtx[marker] = vmtx[base]
        for mask in p.masks:
            vmtx[mask] = vmtx[zero]
    _extend_hvar(font, p)


def _dot(pen, advance: int, x_height: int) -> None:
    """A solid dot: wider than a bullet and sitting at mid x-height, like a password field."""
    r = round(min(advance * 0.3, x_height * 0.36))
    cx, cy = advance / 2, x_height / 2
    k = 0.5523 * r  # cubic circle approximation
    pen.moveTo((cx + r, cy))
    pen.curveTo((cx + r, cy + k), (cx + k, cy + r), (cx, cy + r))
    pen.curveTo((cx - k, cy + r), (cx - r, cy + k), (cx - r, cy))
    pen.curveTo((cx - r, cy - k), (cx - k, cy - r), (cx, cy - r))
    pen.curveTo((cx + k, cy - r), (cx + r, cy - k), (cx + r, cy))
    pen.closePath()


def _x_height(font: TTFont) -> int:
    os2 = font["OS/2"]
    return getattr(os2, "sxHeight", 0) or round(font["head"].unitsPerEm * 0.5)


def _add_glyf(font: TTFont, p: fea.Plan, advance: int) -> None:
    glyf, hmtx = font["glyf"], font["hmtx"]
    gvar = font["gvar"] if "gvar" in font else None

    for mask in p.masks:
        tt = TTGlyphPen(None)
        _dot(Cu2QuPen(tt, max_err=1, reverse_direction=True), advance, _x_height(font))
        g = tt.glyph()
        g.recalcBounds(glyf)
        glyf[mask] = g
        hmtx[mask] = (advance, g.xMin)
        maxp = font["maxp"]
        maxp.maxPoints = max(maxp.maxPoints, len(g.coordinates))
        maxp.maxContours = max(maxp.maxContours, g.numberOfContours)
    for marker, base in p.markers.items():
        # Copy the encoded bytes rather than the decoded glyph, so neither is re-encoded.
        src = glyf.glyphs[base]
        glyf[marker] = Glyph(src.data) if hasattr(src, "data") else copy.deepcopy(src)
        if gvar is not None and base in gvar.variations:
            gvar.variations[marker] = copy.deepcopy(gvar.variations[base])


def _add_cff(font: TTFont, p: fea.Plan, advance: int) -> None:
    cff = font["CFF "].cff
    top = cff.topDictIndex[0]
    strings = top.CharStrings
    cid = hasattr(top, "FDArray")

    def append(name: str, cs: T2CharString, fd: int) -> None:
        strings.charStringsIndex.append(cs)
        strings.charStrings[name] = len(strings.charStringsIndex) - 1
        top.charset.append(name)
        if cid:
            top.FDSelect.gidArray.append(fd)

    def fd_of(name: str) -> int:
        return top.FDSelect[font.getGlyphID(name)] if cid else 0

    base_fd = fd_of(font.getBestCmap()[ord("0")])
    private = top.FDArray[base_fd].Private if cid else top.Private
    # CFF glyph ids follow the charset, so append in glyph order: markers, then masks.
    for marker, base in p.markers.items():
        src = strings[base]
        src.decompile()
        append(marker, T2CharString(program=list(src.program), private=src.private,
                                    globalSubrs=src.globalSubrs), fd_of(base))
    for mask in p.masks:
        pen = T2CharStringPen(advance, None)
        _dot(pen, advance, _x_height(font))
        cs = pen.getCharString(private=private, globalSubrs=cff.GlobalSubrs)
        nominal = getattr(private, "nominalWidthX", 0)
        if nominal:  # the pen writes the width raw; CFF stores it relative to nominalWidthX
            cs.program[0] -= nominal
        append(mask, cs, base_fd)
        font["hmtx"][mask] = (advance, round(advance / 2 - min(advance * 0.3, _x_height(font) * 0.36)))


def _extend_hvar(font: TTFont, p: fea.Plan) -> None:
    """Explicit HVAR maps index by glyph; give new glyphs their source glyph's entry."""
    if "HVAR" not in font:
        return
    hvar = font["HVAR"].table
    zero = font.getBestCmap()[ord("0")]
    for attr in ("AdvWidthMap", "LsbMap", "RsbMap"):
        m = getattr(hvar, attr, None)
        if m is None:
            continue
        for marker, base in p.markers.items():
            m.mapping[marker] = m.mapping[base]
        for mask in p.masks:
            m.mapping[mask] = m.mapping[zero]


# --- lookups --------------------------------------------------------------------------

def _build_lookups(font: TTFont, code: str) -> tuple[list, list[int]]:
    """Compile the feature code against a scratch copy of the font and return its lookups.

    feaLib replaces a font's whole GSUB, so it builds into a copy without one. The first
    two lookups it returns are the named ones that the feature uses, in feature order.
    """
    scratch = TTFont()
    scratch.setGlyphOrder(font.getGlyphOrder())
    addOpenTypeFeaturesFromString(scratch, code, tables=["GSUB"])
    table = scratch["GSUB"].table
    used = table.FeatureList.FeatureRecord[0].Feature.LookupListIndex
    return table.LookupList.Lookup, list(used)


def _prepend_lookups(font: TTFont, built: tuple[list, list[int]], tag: str) -> None:
    lookups, feature_indices = built
    gsub = font["GSUB"].table
    shift = len(lookups)
    for record in _subst_lookup_records(gsub.LookupList):
        record.LookupListIndex += shift
    for feature in _features(gsub):
        feature.LookupListIndex = [i + shift for i in feature.LookupListIndex]
    gsub.LookupList.Lookup = list(lookups) + gsub.LookupList.Lookup
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)

    for feature in _features(gsub, tag):
        feature.LookupListIndex = feature_indices + feature.LookupListIndex
        feature.LookupCount = len(feature.LookupListIndex)
    # A font may use the tag in some scripts only (Liberation Mono has no ccmp in latn).
    records = gsub.FeatureList.FeatureRecord
    missing = [ls for ls in _langsyses(gsub)
               if not any(records[i].FeatureTag == tag for i in ls.FeatureIndex)]
    if missing:
        _add_feature(gsub, tag, feature_indices, missing)


def _ensure_gsub(font: TTFont):
    """The font's GSUB, decompiled, with every list present and at least DFLT and latn
    scripts. Some fonts have no GSUB, or one with null lists (Hermit)."""
    empty = _empty_gsub().table
    if "GSUB" not in font:
        font["GSUB"] = newTable("GSUB")
        font["GSUB"].table = empty
        return empty
    gsub = font["GSUB"].table
    gsub.ensureDecompiled(recurse=True)
    for attr in ("ScriptList", "FeatureList", "LookupList"):
        if getattr(gsub, attr, None) is None:
            setattr(gsub, attr, getattr(empty, attr))
    if not gsub.ScriptList.ScriptRecord:
        gsub.ScriptList.ScriptRecord = empty.ScriptList.ScriptRecord
    return gsub


def _empty_gsub():
    table = newTable("GSUB")
    t = table.table = ot.GSUB()
    t.Version = 0x00010000
    t.ScriptList = ot.ScriptList()
    t.ScriptList.ScriptRecord = []
    for script in ("DFLT", "latn"):
        rec = ot.ScriptRecord()
        rec.ScriptTag = script
        rec.Script = ot.Script()
        rec.Script.DefaultLangSys = ot.LangSys()
        rec.Script.DefaultLangSys.ReqFeatureIndex = 0xFFFF
        rec.Script.DefaultLangSys.FeatureIndex = []
        rec.Script.LangSysRecord = []
        t.ScriptList.ScriptRecord.append(rec)
    t.FeatureList = ot.FeatureList()
    t.FeatureList.FeatureRecord = []
    t.LookupList = ot.LookupList()
    t.LookupList.Lookup = []
    return table


def _features(gsub, tag: str | None = None):
    for i, r in enumerate(gsub.FeatureList.FeatureRecord):
        if tag is None or r.FeatureTag == tag:
            yield r.Feature
    fv = getattr(gsub, "FeatureVariations", None)
    if fv:
        for rec in fv.FeatureVariationRecord:
            for sub in rec.FeatureTableSubstitution.SubstitutionRecord:
                if tag is None or gsub.FeatureList.FeatureRecord[sub.FeatureIndex].FeatureTag == tag:
                    yield sub.Feature


def _subst_lookup_records(node, seen=None):
    """Every nested-lookup reference (SubstLookupRecord) inside contextual lookups."""
    seen = set() if seen is None else seen
    if id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, ot.SubstLookupRecord):
        yield node
        return
    if isinstance(node, list):
        for item in node:
            yield from _subst_lookup_records(item, seen)
    elif isinstance(node, ot.BaseTable):
        for value in vars(node).values():
            if isinstance(value, (list, ot.BaseTable)):
                yield from _subst_lookup_records(value, seen)


def _add_feature(gsub, tag: str, lookup_indices: list[int], langsyses: list) -> None:
    """Add a feature to `langsyses`, keeping the FeatureList sorted by tag."""
    records = gsub.FeatureList.FeatureRecord
    rec = ot.FeatureRecord()
    rec.FeatureTag = tag
    rec.Feature = ot.Feature()
    rec.Feature.FeatureParams = None
    rec.Feature.LookupListIndex = list(lookup_indices)
    rec.Feature.LookupCount = len(lookup_indices)
    new_index = len(records)
    records.append(rec)
    for langsys in langsyses:
        langsys.FeatureIndex.append(new_index)

    order = sorted(range(len(records)), key=lambda i: (records[i].FeatureTag, i))
    remap = {old: new for new, old in enumerate(order)}
    gsub.FeatureList.FeatureRecord = [records[i] for i in order]
    gsub.FeatureList.FeatureCount = len(order)
    for langsys in _langsyses(gsub):
        langsys.FeatureIndex = sorted(remap[i] for i in langsys.FeatureIndex)
        langsys.FeatureCount = len(langsys.FeatureIndex)
        if langsys.ReqFeatureIndex != 0xFFFF:
            langsys.ReqFeatureIndex = remap[langsys.ReqFeatureIndex]
    fv = getattr(gsub, "FeatureVariations", None)
    if fv:
        for v in fv.FeatureVariationRecord:
            for sub in v.FeatureTableSubstitution.SubstitutionRecord:
                sub.FeatureIndex = remap[sub.FeatureIndex]
            v.FeatureTableSubstitution.SubstitutionRecord.sort(key=lambda s: s.FeatureIndex)


def _langsyses(gsub):
    for script in gsub.ScriptList.ScriptRecord:
        if script.Script.DefaultLangSys is not None:
            yield script.Script.DefaultLangSys
        for lang in script.Script.LangSysRecord:
            yield lang.LangSys
