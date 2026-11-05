"""Generate the OpenType feature code that masks secrets.

One chained-context substitution lookup whose rules only use backtrack context, so a
glyph's substitution depends only on what is already drawn before it. Typing or streaming
a secret therefore never changes a glyph once shown. The shaper walks the line left to
right and backtrack context sees the substitutions already made, which gives two rules:

- Mask: a character of a kind's charset becomes the kind's mask glyph when the kind's
  marker and `keep` charset characters are behind it, or when a mask glyph of the same
  kind is directly behind it.
- Marker: the last glyph of a trigger becomes a marker glyph, a copy of that glyph per
  kind (`underscore.sm.alnum`). Shapers keep no state, so the marker is how later rules
  know a secret started and which characters it may contain.
"""

from collections.abc import Mapping, Set
from dataclasses import dataclass

from .patterns import Kind, Patterns, Trigger

WORD_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"


def mask_glyph(kind: Kind) -> str:
    return f"sm.mask.{kind.name}"


def marker_glyph(base: str, kind: Kind) -> str:
    return f"{base}.sm.{kind.name}"


@dataclass(frozen=True)
class Plan:
    """What a font needs for a set of patterns: new glyphs and the feature code."""

    markers: dict[str, str]  # new marker glyph -> glyph it copies
    masks: tuple[str, ...]
    fea: str
    skipped: tuple[Trigger, ...]  # triggers using characters the font has no glyph for


def plan(
    patterns: Patterns,
    cmap: Mapping[int, str],
    variants: Mapping[str, Set[str]],
) -> Plan:
    """`variants[g]` lists glyphs an earlier shaping stage (rvrn) may put in place of `g`."""

    usable = [t for t in patterns.triggers if all(ord(c) in cmap for c in t.text)]
    skipped = tuple(t for t in patterns.triggers if t not in usable)
    kinds = list(dict.fromkeys(t.kind for t in usable))

    markers = {marker_glyph(cmap[ord(t.text[-1])], t.kind): cmap[ord(t.text[-1])] for t in usable}

    def glyphs(ch: str) -> list[str]:
        """The glyphs `ch` may be drawn with when a rule looks back at it: its own, rvrn
        variants, and its marker copies (TOKEN=' still matches after TOKEN= marked the =)."""
        g = cmap[ord(ch)]
        own = [g, *sorted(set(variants.get(g, ())) - {g})]
        # Editors may draw a space as U+00A0: VS Code does in `"password": "`.
        if ch == " " and 0xA0 in cmap and cmap[0xA0] not in own:
            own.append(cmap[0xA0])
        return own + [m for m, base in markers.items() if base in own]

    def cls(chars: str) -> str:
        names = [g for ch in chars if ord(ch) in cmap for g in glyphs(ch)]
        return "[" + " ".join(f"\\{g}" for g in dict.fromkeys(names)) + "]"

    def raw(chars: str) -> str:
        """Glyphs of unmarked characters: what a rule may still replace."""
        names = [g for ch in chars if ord(ch) in cmap for g in glyphs(ch) if g not in markers]
        return "[" + " ".join(f"\\{g}" for g in dict.fromkeys(names)) + "]"

    classes = [f"@sm_boundary = {cls(WORD_CHARS)};", f"@sm_lower = {raw(LOWER)};"]
    # Mask rules come first: inside a masked run every key character stays masked, even
    # one that would end a trigger (the eyJ after a JWT's first dot).
    rules: list[str] = []
    for k in kinds:
        own = " ".join(dict.fromkeys(f"\\{marker_glyph(cmap[ord(t.text[-1])], k)}" for t in usable if t.kind == k))
        mark, charset = f"@sm_marker_{_ident(k)}", f"@sm_cs_{_ident(k)}"
        classes += [f"{mark} = [{own}];", f"{charset} = {raw(k.chars)};"]
        if k.word_filter:
            rules.append(f"    ignore sub {mark} {' '.join(['@sm_lower'] * patterns.keep)} {charset}';")
        rules.append(f"    sub {mark} {' '.join([charset] * patterns.keep)} {charset}' by \\{mask_glyph(k)};")
        rules.append(f"    sub \\{mask_glyph(k)} {charset}' by \\{mask_glyph(k)};")
    for t in usable:
        *before, last = t.text
        context = " ".join(cls(c) for c in before)
        if t.text[0] in WORD_CHARS:
            rules.append(f"    ignore sub @sm_boundary {context} {raw(last)}';")
        rules.append(f"    sub {context} {raw(last)}' by \\{marker_glyph(cmap[ord(last)], t.kind)};")

    fea = "\n".join(
        [
            *classes,
            "",
            "lookup fontsecret {",
            *rules,
            "} fontsecret;",
            "",
            "feature ss20 { lookup fontsecret; } ss20;",
            "",
        ]
    )
    return Plan(markers, tuple(mask_glyph(k) for k in kinds), fea, skipped)


def _ident(kind: Kind) -> str:
    return kind.name.replace(".", "_")
