#!/usr/bin/env bash
# Download one regular face of every family in Nerd Fonts' src/unpatched-fonts to fonts/nf-src,
# named <family>--<file>. Then: uv run python scripts/survey.py fonts/nf-src docs/nerd-fonts-survey.md
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p fonts/nf-src
gh api 'repos/ryanoasis/nerd-fonts/git/trees/master?recursive=1' \
  -q '.tree[] | select(.type=="blob") | select(.path|startswith("src/unpatched-fonts/")) | select(.path|test("\\.(ttf|otf)$";"i")) | .path' |
python3 -c '
import re, sys, collections
fam = collections.defaultdict(list)
for p in sys.stdin.read().splitlines():
    fam[p.split("/")[2]].append(p)
def score(p):
    n = p.split("/")[-1].lower()
    s = -10 if "regular" in n else 0
    if re.search(r"italic|oblique|bold|light|thin|medium|black|semi|heavy|extra|book", n): s += 20
    if "variable" in p.lower() or "[" in n: s += 3  # Nerd Fonts patches static faces
    return (s, len(p))
for f in sorted(fam): print(min(fam[f], key=score))
' |
while read -r path; do
  out="fonts/nf-src/$(echo "$path" | cut -d/ -f3)--$(basename "$path")"
  [ -f "$out" ] || curl -fsSL -o "$out" \
    "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$path")"
done
ls fonts/nf-src | wc -l
