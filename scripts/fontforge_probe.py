"""Probe: can FontForge alone (Nerd Fonts' toolchain) add secret masking?

fontforge -lang=py -script fontforge_probe.py FONT FEA GLYPHS_JSON OUT
Creates marker copies and mask dots, merges the feature file and saves. FontForge appends
the merged lookups after the font's own, so ligatures that consume trigger characters
(Cascadia's --) run first and those triggers miss.
"""
import json
import math
import sys

import fontforge

src, fea_path, glyphs_path, out = sys.argv[1:5]
font = fontforge.open(src)
plan = json.load(open(glyphs_path))
advance = font["zero"].width
xh = font.xHeight or font.em // 2
for marker, base in plan["markers"].items():
    g = font.createChar(-1, marker)
    g.addReference(base)
    g.width = font[base].width
for mask in plan["masks"]:
    g = font.createChar(-1, mask)
    pen = g.glyphPen()
    r = min(advance * 0.3, xh * 0.36)
    cx, cy = advance / 2, xh / 2
    # Eight quadratic arcs (TrueType implied on-curve points); exact enough for a dot and
    # valid in both cubic (CFF) and quadratic (glyf) FontForge layers.
    far = r / math.cos(math.pi / 8)
    off = [(cx + far * math.cos(a), cy + far * math.sin(a))
           for a in (math.pi / 8 + i * math.pi / 4 for i in range(8))]
    pen.moveTo((cx + r, cy))
    pen.qCurveTo(*off[:2], (cx, cy + r))
    pen.qCurveTo(*off[2:4], (cx - r, cy))
    pen.qCurveTo(*off[4:6], (cx, cy - r))
    pen.qCurveTo(*off[6:8], (cx + r, cy))
    pen.closePath()
    pen = None
    g.width = advance
before = list(font.gsub_lookups)
font.mergeFeature(fea_path)
added = [l for l in font.gsub_lookups if l not in before]
print(f"added {len(added)} lookups at positions {font.gsub_lookups.index(added[0])}..{len(font.gsub_lookups) - 1}; "
      "the Python API cannot move them ahead of the font's own lookups")
font.generate(out)
