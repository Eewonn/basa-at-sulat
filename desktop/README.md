# desktop/: teacher and learner app (Windows + Linux)

**Owner:** Frontend · **Design spec:** [../docs/FRONTEND.md](../docs/FRONTEND.md) · **Contract:** [../docs/API.md](../docs/API.md)

**Stack:** Electron (via electron-vite) + React + TypeScript + Vite + Tailwind v4 (`@tailwindcss/vite`, tokens in CSS `@theme`, no `tailwind.config.js`) + Radix UI + lucide-react + TanStack Query. Fonts are bundled with `@fontsource`.

## Run it
Needs Node 22+. The same commands work on Windows and Linux.

```bash
cd desktop
npm install
npm run dev        # opens the app with hot reload
npm run typecheck
npm run build      # production bundle in desktop/out/
```

**Everything the app shows comes from the engine** (`src/renderer/src/api/httpApi.ts`); there is no sample data. **The app starts the engine itself** when it opens (`src/main/engine.ts`): it picks a free port, runs `python -m app` from `engine/` (using `engine/.venv` if it exists, or `BASA_PYTHON`), creates and seeds the database on first run, waits for `/health`, and stops the engine on quit. Data lives in `engine/storage/` unless `BASA_DATA_DIR` says otherwise. For demo checks, run `python -m app.seed --demo` in `engine/` once. `scripts/start.sh` and `BASA_ENGINE_PORT=<port> npm run dev` still work: with a port given, the app uses that engine instead of starting one. If the engine can't start within 180 s, the app says so and points to `scripts/start.sh --check`. Routes the engine doesn't have yet (docs/API.md, "Proposed by frontend") are hidden, never filled with made-up values; what the teacher types for them (class name, a book's category and reader) is kept on the laptop.

**Clickable flow today:** Klase → learner profile (stars, days in a row, reading time, progress trend) → Basahin (pick a story by topic, record with a live waveform) → processing (the tamaraw thinks) → Resulta (tap a word to fix it, I-confirm) → Sanay kid mode (Pakinggan / Sabihin, confetti and stars, reread, done). Pakinggan plays the word cut from a Sulat book (hidden when no book has it), and Sabihin is checked by the aligner; each attempt is saved and a correct one earns a star.

Also built: the **Basa** tab (who's due for a check this week, recent checks), **Sulat** (book library, a 3-step book maker that records a fluent speaker and previews with word highlighting, and a read-along player), and **Settings** (language, text size, privacy and data with delete-all-audio, class roster add/rename, models, about). Books play the recorded model reading, with the highlight following the real audio.

All illustrations are our own SVGs (`components/Art.tsx`), drawn to match Taw the tamaraw (`components/Tamaraw.tsx`). No stock art or icon packs for anything kids see.

## Why Electron
It ships the same Chromium on Windows and Linux, so microphone recording and rendering behave identically. Tauri's Linux webview (WebKitGTK) denies microphone access unless the app adds a custom permission handler.

## Screens, in build order
1. **Scaffold, tokens, AppShell, StatusPill** (P0-FE-1)
2. **Recorder + live waveform** (P0-FE-2)
3. **Review screen on mock data**, the hero of the demo (P0-FE-3)
4. Check setup, processing, first-run system check (mock)
5. **Review on the real API** (P1-FE-1), **learner and passage pickers** (P1-FE-2)
6. **Sanay kid mode** (P2-FE-1), **Sulat books + karaoke** (P2-FE-2), **class view + learner trend** (P2-FE-3)
7. **Polish** (P3-FE-1), **backup demo video** (P3-FE-2)

## Rules
- **Works offline:** no CDN scripts, bundled fonts, strict CSP allowing only `127.0.0.1`.
- **Real data only:** every number and label comes from the engine or the teacher. Nothing is hardcoded or simulated; a missing route hides its feature.
- **Color never stands alone:** every label also shows as text or an icon.
- **Design for 1366×768** (common cheap laptops), and check at 1920×1080 for the demo screen.
- **Cross-platform:** no bash-only scripts, `path.join` everywhere, and test on Windows before each demo.
