# web/: teacher and learner app

**Owner:** Frontend · **Stack:** Next.js 16 (App Router) + TypeScript + Tailwind v4 (config in CSS via `@import "tailwindcss"`, no `tailwind.config.js`) · **Contract:** [../docs/API.md](../docs/API.md)

## Screens, in build order
1. **App shell and UI text file** (P0-FE-1): all UI text in one file, Filipino and English.
2. **Recorder** (P0-FE-2): MediaRecorder on localhost, uploads to `POST /assess`.
3. **Review screen** (P0-FE-3, then P1-FE-1): passage with color-coded words, tap-to-fix, words correct per minute, level, Confirm and Re-record. Build it first against `docs/api/assess.example.json`.
4. **Learner and passage pickers** (P1-FE-2).
5. **Sanay practice** (P2-FE-1): Hear it / Say it / reread, one missed word at a time.
6. **Sulat book maker and player** (P2-FE-2): type a story, record a model reading, play it back with each word highlighted.
7. **Class view** (P2-FE-3): groups by level, draft plans, per-learner progress.

## Rules
- **Works offline:** no CDN scripts, and fonts are self-hosted (P3-FE-1).
- **Color never stands alone:** every label also shows as text or an icon ("misread", "skipped").
- Big tap targets, because teachers use it next to a child, often on a cheap laptop.
- Design reference: the mockups in the team deck (review screen, Sanay screen, class view).
