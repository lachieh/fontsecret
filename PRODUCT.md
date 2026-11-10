# Product

<!-- impeccable:product-schema 1 -->

> Inferred from README.md and the request "a few quick 6 second videos for social media that show what fontsecret does" (2026-11-09). The interview was skipped at Lachlan's standing instruction to proceed on recommendations; every fact below comes from the repository unless marked (inferred).

## Platform

web

## Stack

delegated: social videos are rendered from HTML/CSS/JS in a headless browser and encoded with ffmpeg; no framework (inferred).

## Users

Developers who stream, screen-share, record demos or post screenshots of terminals and editors, and who use AI coding agents that print tokens into their terminal. They want an API key on screen to stop being a leak (inferred from README).

## Product Purpose

`fontsecret` patches an OpenType font so it draws known secrets (API keys, tokens, passwords) as dots after their first 4 characters. It changes only what is drawn: copy/paste, files, shell history and the accessibility tree still get the real characters. Its only purpose is to hide secrets in screenshots, screen sharing, and from someone looking over your shoulder.

## Positioning

The masking lives in the font, so it works in any app that shapes text, with no plugin per app. Rules only look backwards, so a key that is typed or streamed in never shows a secret character before hiding it, not even for one frame. The technique is inspired by Cody Collier's Obel Mono; `fontsecret` adds it to any font.

## Operating Context

Terminals (Ghostty, iTerm2), editors (VS Code), TextEdit; `.env` files, JSON config, `Authorization: Bearer` headers, shell exports; agents streaming output. Opt-in via the private `MASK` feature tag, or always-on via `ccmp`.

## Capabilities and Constraints

- `fontsecret patch IN OUT` (default `MASK` tag, `Masked` suffix), `--feature`, `--always-on`, `--suffix`; `fontsecret verify ORIGINAL PATCHED`.
- Triggers in `patterns.toml`: GitHub `ghp_`, GitLab, Anthropic, OpenAI, AWS, Google, Slack, Stripe, npm, PyPI, Hugging Face, DigitalOcean, Shopify, SendGrid, JWT, password and token assignments, Bearer.
- Limits: not security against software; one shaping run (wrapped keys, Ghostty selection edges and cursor can reveal); no CFF2.

## Brand Commitments

- The name is written `fontsecret`, in code style, lowercase.
- Credit Cody Collier by name only; no pronouns; never @-mention `codycollier` on GitHub.
- Never overclaim: it hides secrets from eyes and cameras, not from software or agents.

## Evidence on Hand

- Patched sample fonts: `fonts/real/CascadiaCodeMasked-Regular.ttf` (always on), `fonts/out/*` (gitignored, built by `scripts/build-samples.sh`).
- Captures: `docs/CascadiaCode.png`, `docs/CascadiaCode-original.png`, `docs/real-*.png`, `docs/demo/*.mp4`.
- Tests: 87 passing; 71/71 Nerd Fonts families pass the survey.
- No users, testimonials, download counts or press exist; do not invent them.

## Product Principles

1. Show the mechanism, not a claim: the real patched font, real shaping.
2. Be exact about the limit: pixels, not text.
3. Never a frame of leak: the streaming property is the product's sharpest edge.
