#!/usr/bin/env bash
# Fetch OFL monospace fonts and patch them.
#   fonts/out:  variable Cascadia Code (glyf) and Source Code Pro (CFF), always on and opt-in, for the tests
#   fonts/real: static Cascadia Code, always on and under the private MASK tag, for scripts/real-apps.sh
set -euo pipefail
cd "$(dirname "$0")/.."
in=fonts/in out=fonts/out real=fonts/real
mkdir -p "$in" "$out" "$real"
fetch() { [ -f "$in/$2" ] || { curl -fsSL -o "$in/$1.zip" "$3" && unzip -q -o -j "$in/$1.zip" "$4" -d "$in" && rm "$in/$1.zip"; }; }
fetch cascadia CascadiaCode.ttf \
  https://github.com/microsoft/cascadia-code/releases/download/v2407.24/CascadiaCode-2407.24.zip 'ttf/CascadiaCode.ttf'
fetch scp SourceCodePro-Regular.otf \
  'https://github.com/adobe-fonts/source-code-pro/releases/download/2.042R-u%2F1.062R-i%2F1.026R-vf/OTF-source-code-pro-2.042R-u_1.062R-i.zip' 'OTF/SourceCodePro-Regular.otf'
for f in CascadiaCode.ttf SourceCodePro-Regular.otf; do
  stem=${f%.*} ext=${f##*.}
  uv run python -m fontsecret patch "$in/$f" "$out/$stem-Masked.$ext" --always-on
  uv run python -m fontsecret patch "$in/$f" "$out/$stem-MASK.$ext" --suffix MASK
done
fetch cascadia-static CascadiaCode-Regular.ttf \
  https://github.com/microsoft/cascadia-code/releases/download/v2407.24/CascadiaCode-2407.24.zip 'ttf/static/CascadiaCode-Regular.ttf'
uv run python -m fontsecret patch "$in/CascadiaCode-Regular.ttf" "$real/CascadiaCodeMasked-Regular.ttf" --always-on
uv run python -m fontsecret patch "$in/CascadiaCode-Regular.ttf" "$real/CascadiaCodeMASK-Regular.ttf" --suffix MASK
