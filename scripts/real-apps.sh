#!/usr/bin/env bash
# Show the patched fonts in real macOS apps.
#
#   scripts/real-apps.sh install      copy the two test fonts to ~/Library/Fonts
#   scripts/real-apps.sh ghostty      Ghostty, "Cascadia Code SMSK" with font-feature +SMSK (CoreText)
#   scripts/real-apps.sh ghostty-on   Ghostty, always-on "Cascadia Code Masked"
#   scripts/real-apps.sh iterm        iTerm2 dynamic profile, "Cascadia Code Masked", ligatures on (CoreText)
#   scripts/real-apps.sh textedit     TextEdit, "Cascadia Code Masked" (CoreText, no settings)
#   scripts/real-apps.sh vscode       VS Code, "Cascadia Code SMSK" with fontLigatures "'SMSK'" (Chromium)
#   scripts/real-apps.sh uninstall    remove the fonts, the iTerm2 profile and the test files
#
# Run scripts/build-samples.sh first.
set -euo pipefail
cd "$(dirname "$0")/.."
FONTS=(CascadiaCodeMasked-Regular.ttf CascadiaCodeSMSK-Regular.ttf)
WORK=/tmp/fontsecret-real
ITERM_PROFILE="$HOME/Library/Application Support/iTerm2/DynamicProfiles/fontsecret.json"

sample() {
  mkdir -p "$WORK/vscode/.vscode"
  # Fake keys in real formats. Nothing here is a live credential.
  cat > "$WORK/sample.txt" <<'TXT'
GITHUB_TOKEN=ghp_Xk9QzR2mLp7vB4nT8wYc1dFh
export ANTHROPIC_API_KEY=sk-ant-api03-Ab_cd-EfGhIjKl
{"password": "correct-horse-battery"}
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIi"
AKIAIOSFODNN7EXAMPLE  MONKEY=banana  token: string
a == b -> c  // ligatures untouched
TXT
  head -2 "$WORK/sample.txt" | sed 's/^export //' > "$WORK/vscode/.env"
  printf '{\n  "password": "correct-horse-battery",\n  "github": "ghp_Xk9QzR2mLp7vB4nT8wYc1dFh"\n}\n' > "$WORK/vscode/config.json"
}

case "${1:-}" in
  install)
    for f in "${FONTS[@]}"; do cp "fonts/real/$f" "$HOME/Library/Fonts/$f"; done
    /Applications/Ghostty.app/Contents/MacOS/ghostty +list-fonts --family="Cascadia Code SMSK" | head -3
    ;;
  ghostty | ghostty-on)
    sample
    family="Cascadia Code SMSK" feature=(--font-feature=+SMSK)
    [ "$1" = ghostty-on ] && family="Cascadia Code Masked" feature=()
    open -na Ghostty.app --args --font-family="$family" "${feature[@]}" --font-size=16 \
      --window-width=90 --window-height=12 --title="fontsecret $1" \
      --command="/bin/sh -c 'cat $WORK/sample.txt; exec sleep 3600'"
    ;;
  iterm)
    sample
    mkdir -p "$(dirname "$ITERM_PROFILE")"
    cat > "$ITERM_PROFILE" <<JSON
{"Profiles": [{"Name": "fontsecret", "Guid": "fontsecret-test-profile",
  "Normal Font": "CascadiaCodeMasked-Regular 16", "ASCII Ligatures": true, "Non-ASCII Ligatures": true,
  "Custom Command": "Yes", "Command": "/bin/sh -c 'cat $WORK/sample.txt; exec sleep 3600'",
  "Columns": 90, "Rows": 12}]}
JSON
    sleep 1  # iTerm2 reloads dynamic profiles when the file changes
    osascript -e 'tell application "iTerm" to create window with profile "fontsecret"'
    ;;
  textedit)
    sample
    {
      printf '{\\rtf1\\ansi{\\fonttbl\\f0\\fnil CascadiaCodeMasked-Regular;}\\f0\\fs32 '
      sed -e 's/\\/\\\\/g; s/{/\\{/g; s/}/\\}/g; s/$/\\/' "$WORK/sample.txt"
      printf '}\n'
    } > "$WORK/sample.rtf"
    open -a TextEdit "$WORK/sample.rtf"
    ;;
  vscode)
    sample
    cat > "$WORK/vscode/.vscode/settings.json" <<'JSON'
{
  "editor.fontFamily": "'Cascadia Code SMSK'",
  "editor.fontLigatures": "'SMSK', 'calt'",
  "editor.fontSize": 16
}
JSON
    open -na "Visual Studio Code.app" --args --new-window "$WORK/vscode" "$WORK/vscode/.env" "$WORK/vscode/config.json"
    ;;
  uninstall)
    for f in "${FONTS[@]}"; do rm -f "$HOME/Library/Fonts/$f"; done
    rm -f "$ITERM_PROFILE"
    rm -rf "$WORK"
    ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
