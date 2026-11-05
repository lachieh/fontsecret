# fontsecret

fontsecret patches an OpenType font so it draws known secret tokens as dots.

The idea and the technique come from [Cody Collier](https://x.com/codycollier)'s
[Obel Mono](https://typographic.systems/obel-mono), a typeface with secret masking built in,
described in the post
[A typeface that keeps a secret](https://typographic.systems/journal/a-typeface-that-keeps-a-secret).
fontsecret reimplements that technique with fontTools so it can be added to fonts that
don't have it. See [Credits](#credits).

![Cascadia Code, patched](docs/CascadiaCode.png)

The text in that image contains the full secrets. Only the drawing changes: copy/paste,
files, shell history and the accessibility tree still hold the real characters.
[Unpatched, for comparison](docs/CascadiaCode-original.png).

```sh
mise install && uv sync
./scripts/build-samples.sh    # downloads OFL fonts into fonts/ and patches them
uv run pytest                 # 78 tests, shaping with HarfBuzz
uv run python -m fontsecret patch IN.ttf OUT.ttf --always-on --suffix Masked
uv run python -m fontsecret verify IN.ttf OUT.ttf
```

## How the masking works

Masking is ordinary GSUB chained-context substitution (lookup type 6), the mechanism that
builds ligatures. This is Cody Collier's design for Obel Mono, as the post describes it. I
confirmed the details by decompiling Obel Mono's GSUB and shaping probe strings with
`hb-shape`.

- Every rule looks only at glyphs before it. A glyph never changes once drawn, so typed or
  streamed text never shows a key briefly before hiding it.
- Shapers keep no state between glyphs. The last character of a trigger (the `_` in `ghp_`,
  the `=` in `TOKEN=`) becomes a marker: an identical-looking copy of that glyph, one per
  charset.
- After a marker, 4 charset characters stay visible. The 5th becomes a dot, and so does every
  charset character after a dot. The first character outside the charset ends the mask.

Obel Mono puts the rules in `ccmp` in its Masked build and in `ss01` in the regular build.
fontsecret follows the same split: `--always-on` or an opt-in feature.

## What fontsecret does

1. `fontsecret/fea.py` turns `patterns.toml` and the font's cmap into one lookup. Mask
   rules come before marker rules, so a trigger inside a masked run can't restart it. (The
   `.eyJ` partway through a JWT revealed 4 characters before this.)
2. `fontsecret/font.py` adds the dot and marker glyphs. It supports `glyf` and `CFF`, static
   and variable. Each marker copies the bytes and `gvar` deltas of the exact glyph it
   replaces, so it draws and interpolates the same. (OpenDyslexic's U+00A0 is twice as wide
   as its space, so it gets its own marker.) Glyphs the patcher didn't add are never re-encoded: Iosevka only
   passes OTS in its original encoding.
3. The lookup is prepended to the font's GSUB, and every existing lookup reference is
   shifted. Masking therefore runs before the font's own ligatures and alternates and sees
   the characters as typed.
4. `--always-on` attaches it to `ccmp`. `--feature TAG` uses any tag. With neither, it uses
   the highest free `ssNN`.

Triggers match a non-breaking space wherever they contain a space, because VS Code draws
some spaces as U+00A0.

Where fontsecret differs from Obel Mono Masked:

| Input | Obel Mono Masked | fontsecret | Reason |
|---|---|---|---|
| `ghp_abcdefghXYZ1` | visible | `ghp_abcd••••••••` | Obel treats 4 lowercase letters after a prefix as a word. That would leave about 3 % of GitHub tokens visible. |
| `password=hunter22` | visible | `password=hunt••••` | Passwords often start with a word, so password names never use the word filter. |
| `token: Abcd1234zz` | visible | `token: Abcd••••••` | `name: ` is a trigger for key names. The word filter keeps `token: string` visible. |

## Checking a patched font

A font decides what text looks like, so a modified font could draw `ls` where the text says
`curl evil.sh | sh`. `fontsecret verify ORIGINAL PATCHED` checks that a patched font differs
from its original only by masking:

- Every original glyph keeps its outline bytes, variation data and metrics, and every
  character keeps its glyph (`cmap`).
- Added glyphs are dots (one shape, inside one cell) or copies that draw exactly like an
  original glyph.
- Every original lookup, feature and script is unchanged, apart from the added masking
  feature.
- Added lookups only replace a glyph with a dot, or with a copy that draws and varies exactly
  like the glyph it replaces.
- Every other table is byte-identical. The exceptions are fields that must change when glyphs
  are added, such as `hhea.numberOfHMetrics`.

`tests/test_verify.py` makes six hostile edits to a patched font, on both the glyf and CFF
builds, and checks `verify` rejects each one: remapping `l` to `s` in `cmap`, redrawing `a`
as `o`, a marker that draws as a different glyph, an added substitution of `a` with `b`, an
edited original lookup, and an opt-in lookup attached to an always-on feature.

Run across the 71 Nerd Fonts families, `verify` found three patcher bugs, all fixed. A
non-breaking space was replaced by a copy of a narrower space, and the patcher rewrote
`cmap` and `OS/2` instead of keeping their bytes.

## Verification

- **Tests** (`tests/test_masking.py`, on variable Cascadia Code and CFF Source Code Pro):
  - 24 masking cases, including near-misses like `MONKEY=banana`.
  - No redraws: for 324 lines, every prefix draws as the start of the whole line. A
    planted lookahead rule fails this test.
  - Plain code shapes exactly as in the original font, under each of the original's features.
  - Every output passes OTS and `fontsecret verify` (`tests/test_verify.py`).
- **Every Nerd Fonts family:** `scripts/survey.py` ran the same checks on one face of each of
  the 71 families in Nerd Fonts' `src/unpatched-fonts/`, plus `verify`. All 71 pass
  ([table](docs/nerd-fonts-survey.md)).
- **CoreText:** `scripts/coretext_check.swift` shapes with the macOS engine and matches
  HarfBuzz ([render](docs/coretext-mask.png)).
- **Real apps**, captured with [agent-desktop](https://github.com/vercel-labs/agent-desktop):

  | App | Build | Result |
  |---|---|---|
  | Ghostty 1.3.1 | `font-feature = +MASK` | Masked ([capture](docs/real-ghostty-mask.png)) |
  | TextEdit | always on | Masked ([capture](docs/real-textedit-masked.png)) |
  | TextEdit, typing one key every 200 ms | always on | No frame showed more than the 4 kept characters ([frames](docs/real-textedit-typing.png)) |
  | VS Code | `editor.fontLigatures: "'MASK', 'calt'"` | Masked in `.env` ([capture](docs/real-vscode-env.png)) and in JSON, with and without a space after the colon ([capture](docs/real-vscode-json.png)) |

DirectWrite (Windows), iTerm2 and Terminal.app are untested.

## Selecting text and the cursor

Selecting text paints a background behind glyphs that are already shaped, so selection alone
doesn't reveal anything. The risk is an app that shapes the text on each side of a selection
edge, or of the cursor, as separate runs. The rules only look backwards, so the part after
the split has no marker behind it and draws as typed.

![A selection that starts inside the first key, in Ghostty, TextEdit and VS Code](docs/demo/selection.png)

The selection starts inside the dots of the first key and ends after the password line.

| App | Selection starting inside a key | Select all | Cursor inside a key |
|---|---|---|---|
| Ghostty 1.3.1 | **Shows the selected part of the key** ([video](docs/demo/ghostty.mp4)) | Masked | **Shows the key from the cursor on**, unless `font-shaping-break = no-cursor` |
| TextEdit | Masked ([video](docs/demo/textedit.mp4)) | Masked | Masked |
| VS Code | Masked, the selected dots only change colour ([video](docs/demo/vscode.mp4)) | Masked | Masked |

![Ghostty with the cursor inside a key: default, then font-shaping-break = no-cursor](docs/demo/cursor.png)

Ghostty splits shaping runs under the cursor by default (`font-shaping-break = cursor`) so
that you can see the individual characters of a ligature you're editing. Setting
`font-shaping-break = no-cursor` keeps a key masked with the cursor inside it. No setting
stops the split at a selection edge. A fix belongs in Ghostty: shaping each run with the
text before it as context (HarfBuzz supports this) would keep the marker visible to the
rules. Obel Mono uses the same rules, so it shows the same behaviour.

## Limits

- Masking changes pixels, not text. Anything that reads the text gets the secret. That
  includes AI agents reading the accessibility tree. Rotate a key that has been shown.
- It works within one shaping run. A key that wraps shows on its second line. In Ghostty, a
  selection edge or the cursor inside a key shows the rest of it (see above). Terminals that
  don't shape text, like Alacritty, show everything.
- Text typed before existing text on the same line joins the open key until the line ends.
- On macOS, CoreText uses a font's AAT `morx` table instead of GSUB. ProFont is the only
  Nerd Fonts family with one.
- `CFF2` variable fonts aren't supported.
- `--suffix` only appends to the family name. A font with a Reserved Font Name, such as
  Source Code Pro ("Source"), needs a full rename before you share a modified copy.

## Feature tag

`ss01` can't be a shared convention. 30 of the 71 Nerd Fonts families already use it, and
every tag from `ss01` to `ss20` is used by at least one family.

fontsecret uses the private tag `MASK`. The OpenType spec reserves four uppercase letters
for private features, and registered tags are lowercase, so a private tag can't collide with
a future registered one. There's no prefix convention like HTTP's `X-`. Fonts that use
private tags name them with a 4-letter abbreviation instead: Iosevka uses `HSKL` for its Haskell
ligature set and `JSPT` for JavaScript. None of the 71 Nerd Fonts families uses `MASK`.

`--feature MASK` works in HarfBuzz, CoreText, Ghostty and VS Code, and passes OTS. Tags are
case-sensitive: lowercase `mask` does nothing. A private tag can't carry a display name,
unlike `ssNN`.

The path to a standard tag:

1. Ship `MASK` and an always-on (`ccmp`) build.
2. Ask Cody Collier to add `MASK` to Obel Mono.
3. Nominate lowercase `mask` to Microsoft's registry, with both fonts as evidence. It isn't
   registered yet.

## Nerd Fonts

Nerd Fonts is the right upstream. Powerline isn't: `powerline/fonts` and
`powerline/fontpatcher` last changed in 2024 and 2023, and both only add glyphs.

- **No upstream change needed:** fontsecret works before or after `font-patcher`, tested both
  ways with the `nerdfonts/patcher` Docker image. A small wrapper lets `font-patcher --postprocess` run it on each output.
- **Recommended PR:** a `--secret-mask` option that runs fontsecret after `generate()`. Nerd
  Fonts already uses fontTools in `bin/scripts/fpfix.py` and its CI. Its Docker image would
  need fontTools added.
- **Pure FontForge:** `font.mergeFeature()` imports the rules, but appends them after the
  font's own lookups. In static Cascadia the `--` ligature then runs first, so
  `--token Abc12345` isn't masked. `scripts/fontforge_probe.sh` reproduces this.

Their `contributing.md` asks for an issue before a PR, small PRs, and AI use flagged in the
PR description and in each affected commit message. `font-patcher --experimental` is where an
opt-in feature starts.

Questions for that issue:

- A shared private tag, or always-on `ccmp`?
- Should released Nerd Fonts include masking, or should it stay a `font-patcher` option?
- Who maintains `patterns.toml` as token formats change?

## Files

- `patterns.toml`: triggers, charsets and their sources.
- `fontsecret/`: `patterns.py` loads patterns, `fea.py` generates the rules, `font.py`
  patches the font, `verify.py` checks a patched font, `__main__.py` is the CLI.
- `tests/`: HarfBuzz shaping tests and `verify` tamper tests.
- `docs/demo/`: selection and cursor recordings.
- `scripts/build-samples.sh`: downloads and patches the sample fonts.
- `scripts/fetch-nerd-fonts.sh`, `scripts/survey.py`: the Nerd Fonts survey.
- `scripts/real-apps.sh`, `scripts/coretext_check.swift`: macOS app tests.
  `real-apps.sh uninstall` removes what it installs.
- `scripts/fontforge_probe.sh`: the pure-FontForge attempt.

## Credits

[Cody Collier](https://x.com/codycollier) ([Typographic Systems](https://typographic.systems),
[A90](https://a90.com)) designed secret masking in a font and built it into
[Obel Mono](https://typographic.systems/obel-mono). fontsecret takes these ideas from Obel Mono:

- masking secrets with OpenType substitution rules
- rules that only look backwards, so streamed or typed text never shows a key before hiding it
- a marker glyph that records where a secret starts, and one mask glyph per charset
- keeping the first 4 characters visible, drawing the rest as dots, and ending the mask at
  the first character that can't be part of a key
- an always-on build next to an opt-in feature

fontsecret's code, rules, glyphs and `patterns.toml` were written independently. Obel Mono
(SIL OFL 1.1) was used only for study: decompiling its GSUB and comparing its output. Nothing
from its font files is in this repository, and fontsecret is not affiliated with or endorsed
by Cody Collier.

## License

MIT. The fonts fontsecret downloads keep their own licenses (SIL OFL 1.1 for every sample font).
