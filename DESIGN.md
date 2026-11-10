---
name: fontsecret
description: Letterpress poster proofs pulled in two inks, where the code is set in the real patched font.
colors:
  stock: "#ff5b1a"
  ink: "#161631"
typography:
  display:
    fontFamily: "Shoulders, Impact, sans-serif"
    fontSize: "176px"
    fontWeight: 900
    lineHeight: 0.88
    letterSpacing: "-0.005em"
    fontVariation: "'opsz' 72"
  headline:
    fontFamily: "Shoulders, Impact, sans-serif"
    fontSize: "104px"
    fontWeight: 900
    lineHeight: 0.88
    letterSpacing: "-0.005em"
    fontVariation: "'opsz' 72"
  headline-two-line:
    fontFamily: "Shoulders, Impact, sans-serif"
    fontSize: "120px"
    fontWeight: 900
    lineHeight: 0.88
    letterSpacing: "-0.005em"
    fontVariation: "'opsz' 72"
  keycap:
    fontFamily: "Shoulders, Impact, sans-serif"
    fontSize: "68px"
    fontWeight: 900
    lineHeight: 1
  title:
    fontFamily: "Shoulders, Impact, sans-serif"
    fontSize: "46px"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.02em"
    fontVariation: "'opsz' 40"
  label:
    fontFamily: "Shoulders, Impact, sans-serif"
    fontSize: "34px"
    fontWeight: 800
    letterSpacing: "0.14em"
    fontVariation: "'opsz' 24"
  code:
    fontFamily: "Cascadia Plain, monospace"
    fontSize: "60px"
    fontWeight: 600
    lineHeight: 1.42
  code-masked:
    fontFamily: "Cascadia Masked, monospace"
    fontSize: "60px"
    fontWeight: 600
    lineHeight: 1.42
  name:
    fontFamily: "Cascadia Plain, monospace"
    fontSize: "84px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.02em"
  slug:
    fontFamily: "Cascadia Plain, monospace"
    fontSize: "30px"
    fontWeight: 600
    fontFeature: "'tnum' 1"
rounded:
  keycap: "14px"
spacing:
  key-gap: "16px"
  slug-foot: "46px"
  margin: "64px"
  headline-top: "72px"
components:
  headline:
    textColor: "{colors.ink}"
    typography: "{typography.display}"
  code-line:
    textColor: "{colors.ink}"
    typography: "{typography.code-masked}"
  selection:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.stock}"
    typography: "{typography.code-masked}"
  keycap:
    backgroundColor: "{colors.stock}"
    textColor: "{colors.ink}"
    typography: "{typography.keycap}"
    rounded: "{rounded.keycap}"
    size: "100px"
  label:
    textColor: "{colors.ink}"
    typography: "{typography.label}"
  slug:
    textColor: "{colors.ink}"
    typography: "{typography.slug}"
  lockup-name:
    textColor: "{colors.ink}"
    typography: "{typography.name}"
  lockup-line:
    textColor: "{colors.ink}"
    typography: "{typography.title}"
  lockup-rule:
    backgroundColor: "{colors.ink}"
    height: "7px"
  roller:
    backgroundColor: "{colors.ink}"
    height: "128px"
---

# Design System: fontsecret

## Overview

**Creative North Star: "The Composing Room Proof"**

Every frame is a press proof: fluorescent orange stock, one blue-black ink, pulled by hand. A font is a set of metal sorts, and `fontsecret` swaps a secret's sorts for a dot as they are set. The system exists to show that mechanism on a poster, never to dress up a terminal screenshot; the code is not a picture of code, it is the real patched Cascadia Code shaped live by the browser, inked like everything else on the sheet.

The sheet is a full-bleed 1080 × 1350 (4:5) field with a single left margin that everything hangs from. Wood type shouts across the top third, the code line is the hero across the middle, a second wood-type line answers it, and the `fontsecret` lockup and a printer's slug close the foot. Density comes from texture, not tone: paper fibres in the stock and hard-edged voids where the ink missed. There are exactly two colours: no grays, no gradients, no shading, no device chrome.

Motion is printing. Elements do not fade, slide or scale into place; they are *impressed*: ink coverage builds from sparse grain to solid in a quarter of a second. The only things that travel are tools of the press and the desk: an inking roller, a selection sweep, a caret.

**Key Characteristics:**
- Two colours only: orange stock and blue-black ink, with nothing in between.
- Wood-type display (Shoulders, Big Shoulders 900) against the real patched monospace (Cascadia Code).
- One left margin (64 px) for every element; one focal hub per sheet (the code line).
- Texture everywhere: fibre noise in the stock, hard-thresholded grain and blotch voids in the ink.
- The impression is the only entrance; the roller and the selection are the only sweeps.

## Colors

A two-ink letterpress palette: fluorescent stock and a single blue-black ink, and nothing else.

### Primary
- **Blaze Stock** (`stock`): the paper. Full bleed on every sheet and the page itself; the knock-out colour where ink is reversed (text inside the selection); the bare paper showing through every ink void and the highlight bands on the roller. Carries a multiply fibre texture at 55 % opacity so it is never a flat fill.

### Neutral
- **Press Ink** (`ink`): the one ink. Every glyph, rule, keycap stroke, roller body, selection block and caret. Its coverage is broken by hard-edged voids, so bare stock shows through solid areas.

### Named Rules
**The Two Inks Rule.** Stock and ink are the only colours on the sheet. Every pixel is one or the other (the fibre texture aside); there is no shade, tint, blend or mid-tone used as a design element.

**The Reverse Rule.** When ink fills an area (selection), the type inside it prints in stock, not in a lighter ink.

## Typography

**Display Font:** Shoulders (Big Shoulders, variable with an opsz axis; fallback Impact, sans-serif)
**Code Font:** Cascadia Plain (stock Cascadia Code) and Cascadia Masked (the `fontsecret`-patched Cascadia Code), loaded side by side (fallback monospace)

**Character:** Chicago wood type set at poster scale against a working programmer's monospace. The wood type does the shouting; the monospace is the evidence.

### Hierarchy
- **Display** (Shoulders 900, 176 px, line-height 0.88, opsz 72, uppercase): the opening claim, one or two lines from the top margin.
- **Headline** (Shoulders 900, 104 px one line / 120 px two lines, line-height 0.88, opsz 72, uppercase): the answering line below the code.
- **Keycap** (Shoulders 900, 68 px, line-height 1): the single letter on a keycap.
- **Code** (Cascadia Masked or Cascadia Plain 600, 54–60 px; 1.42 line-height for multi-line blocks): the hero. 60 px for a streamed line, 54 px for a four-line `.env`, 58 px for a selected line. The clipboard paste is Cascadia Plain 700.
- **Name** (Cascadia Plain 700, 84 px, -0.02em, line-height 1): `fontsecret` in the lockup, lowercase, always in the code face.
- **Title** (Shoulders 800, 46 px, opsz 40, +0.02em, uppercase): the lockup's one-line description.
- **Label** (Shoulders 800, 34 px, opsz 24, +0.14em, uppercase): names a container of content (the clipboard). Never a lead-in to a headline.
- **Slug** (Cascadia Plain 600, 30 px, tabular figures): the printer's slug at the foot.

### Named Rules
**The Real Sorts Rule.** Masked text is always set in Cascadia Masked and shaped by the browser. Never draw dots, overlay them, or substitute characters in the source string; the dots must come from the font.

**The Lowercase Name Rule.** `fontsecret` is set in the code face, lowercase, wherever it appears; it is never set in the wood type.

## Layout

A fixed 1080 × 1350 sheet with absolute positions; there is no responsive behaviour. Every element hangs from one left edge at the margin (64 px); full-width elements (headline box, lockup rule, slug) also stop at the 64 px right margin. Nothing is centred.

Vertical bands, shared by all three sheets:
- **Display:** top at 72 px.
- **Hero code:** 300–600 px (the `.env` block at 300; the streamed lines at 500 and 590; the selected line at 450, with keycaps 100 px below it, the label at +236 and the paste at +278).
- **Answer headline:** 690–860 px (740 in A, 690 in B, 860 in C).
- **Lockup:** rule at 1010 px, name 34 px below the rule, description 134 px below the rule.
- **Slug:** 46 px above the bottom edge, frame count flush left, font credit flush right.

### Named Rules
**The One Margin Rule.** Every element starts at the 64 px left margin; type and rules that span the sheet end at the 64 px right margin. One thing may cross the right trim: a secret (see the Bleed, Never Wrap Rule).

**The Bleed, Never Wrap Rule.** A code line is set `white-space: pre` and never wraps. A key longer than the measure bleeds off the right edge of the sheet, because a key broken across two lines leaves the shaping run and shows its real characters.

**The One Hub Rule.** Each sheet has one focal hub, the code line; the headlines frame it above and below, and the lockup only lands after it has done its work.

## Elevation & Depth

Flat. There are no shadows, no deboss, no layering and no shading of any kind: a sheet is one plane of stock with ink on it. The only material cues are texture. The stock carries a fractal-noise fibre layer in multiply. The ink is cut by a hard-threshold void mask (fine grain plus broad blotches; alpha `-40 × noise + 40 × threshold`), so the voids are crisp holes of bare stock, not soft fades; a 2 px displacement warp roughens every edge.

### Named Rules
**The Flat Sheet Rule.** No `box-shadow`, offset shadows, glows, blurs, deboss edges or shaded copies. Depth is never drawn; the press only leaves ink or bare stock.

**The Fine Forme Rule.** Code-size text prints at a fuller threshold (1.12) than display type (1.0), so its dots stay solid and readable while the wood type keeps visible voids.

## Shapes

Hard, square forms: type, solid rules, rectangular selection blocks, a solid roller body. The rounded forms are the keycap (14 px radius inside a 7 px stroke) and the ends of the roller, both depicting real objects, both at 14 px. Strokes and rules share one weight (7 px).

## Components

### Impression (motion primitive)
The entrance for every element. Coverage runs 0→1 over 0.24 s with an exponential ease-out (`1 - 2^(-10p)`); the void threshold climbs from 0.55 (sparse grain) to full (1.0 display, 1.12 code-size text). Elements with no start time are printed from frame 1. Entrances are staggered by start time, never by opacity fades or transforms; rules may additionally draw left to right with `scaleX` (0.35 s).

### Roller
An inking roller: a solid ink body 128 px high, inset 28 px from both trims with 14 px rounded ends (the keycap radius), carrying the press texture. Stock bands turn the cylinder: three across its upper curve (at 20, 40 and 54 px from the top; 12, 6 and 3 px high) and one 4 px band at 104 px on the lower curve. It makes one pass down the code block over 1.5 s with a cubic ease-in-out; above its line of contact the code is set in Cascadia Masked, below it in Cascadia Plain. It is hidden before and after its pass.

### Keycaps
- **Shape:** 100 px square, 7 px ink stroke, softly rounded corners (14 px), stock fill, 16 px gap.
- **Content:** a single wood-type letter (Shoulders 900, 68 px) or a stroked SVG glyph (52 px, 2.5 stroke, round caps) for symbols such as ⌘.
- **Behaviour:** impressed as a pair, like any other forme.

### Selection
A solid ink block (line height × 1.36, starting 6 px above the code line) that sweeps right over 0.7 s with the exponential ease-out. The selected text is reprinted in stock over it (the Reverse Rule), clipped to the sweep relative to the text's own width so every selected glyph reverses.

### Slug
The printer's slug at the foot: `FRAME 001/180` flush left, a short credit (`Cascadia Code` / `Cascadia Code, patched`) flush right, in Cascadia Plain 600 at 30 px with tabular figures. The right side may change once to report state (it gains "patched" when the roller has finished). State is a mark in the slug, never a hue change.

### Lockup
The closing stamp: a 7 px full-width ink rule drawn left to right from 4.3 s, then `fontsecret` (Cascadia Plain 700, 84 px) impressed at 4.45 s, then the one-line description (Shoulders 800, 46 px, uppercase) at 4.65 s. Same position (rule at 1010 px) on every sheet, holding for the last 1.35 s.

### Code Line and Caret
Cascadia Plain or Cascadia Masked at the margin, never wrapped. Streamed text advances by whole characters (0.6 em cell). The caret is an ink block 0.6 em × 1.2 em that follows the last character and blinks at 2.5 Hz once streaming stops.

## Do's and Don'ts

### Do:
- **Do** keep every sheet to stock and ink, with ink voids that cut to bare stock.
- **Do** run every entrance through the impression (0.24 s exponential ease-out, threshold 0.55 to full).
- **Do** set masked text in Cascadia Masked and let the browser shape it.
- **Do** hang every element from the 64 px left margin and keep the lockup at 1010 px and the slug 46 px from the foot.
- **Do** let a long key bleed off the right edge rather than wrap.
- **Do** report state changes in the slug's text.

### Don't:
- **Don't** introduce a third colour, a gray, a tint, a shade or a gradient fill.
- **Don't** fade, slide or scale elements in; type is impressed, not animated.
- **Don't** draw or overlay dots to simulate masking.
- **Don't** add shadows, glows, blurs or deboss edges.
- **Don't** wrap a code line to fit the measure.
- **Don't** set `fontsecret` in the wood type or in capitals.
- **Don't** use the tracked uppercase label as a kicker above a headline; it only names a container of content.
