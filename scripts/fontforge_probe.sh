#!/usr/bin/env bash
# Run fontforge_probe.py in the Nerd Fonts patcher image against FONT (a static font file).
# Writes FONT's feature file next to it and the FontForge-built font as <stem>-ff.<ext>.
set -euo pipefail
cd "$(dirname "$0")/.."
font=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
dir=$(dirname "$font") file=$(basename "$font") stem=${file%.*} ext=${file##*.}
uv run python - "$font" <<'PY'
import json, sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontsecret import fea, patterns
path = Path(sys.argv[1])
f = TTFont(path)
p = fea.plan(patterns.load(), f.getBestCmap(), {})
systems = [("DFLT", "dflt")]
if "GSUB" in f:
    systems = []
    for s in f["GSUB"].table.ScriptList.ScriptRecord:
        systems += [(s.ScriptTag, "dflt")] + [(s.ScriptTag, l.LangSysTag.strip()) for l in s.Script.LangSysRecord]
# Without languagesystem statements FontForge attaches the feature to DFLT only.
head = "".join(f"languagesystem {s} {l};\n" for s, l in systems)
code = p.fea.replace("feature ss20", "feature ccmp").replace("} ss20;", "} ccmp;")
path.with_suffix(".fea").write_text(head + code)
path.with_suffix(".json").write_text(json.dumps({"markers": p.markers, "masks": list(p.masks)}))
PY
docker run --rm --entrypoint fontforge -v "$dir:/w" -v "$PWD/scripts:/s:ro" nerdfonts/patcher:latest \
  -lang=py -script /s/fontforge_probe.py "/w/$file" "/w/$stem.fea" "/w/$stem.json" "/w/$stem-ff.$ext" 2>&1 | grep '^added'
