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

With no engine running, the app uses **sample data** (`src/renderer/src/api/mockApi.ts`) and says so in the status pill. Once the engine exists, start the app with `BASA_ENGINE_PORT=<port>` and it switches to the real API (`httpApi.ts`). Later the app will start the engine itself (P0-FE-4).

**Clickable flow today:** Klase → learner profile (stars, days in a row, reading time, progress trend) → Basahin (pick a story by topic, record with a live waveform) → processing (the tamaraw thinks) → Resulta (tap a word to fix it, I-confirm) → Sanay kid mode (Pakinggan / Sabihin, confetti and stars, reread, done). Pakinggan and the Sabihin result are simulated until the engine exists.

Also built: the **Basa** tab (who's due for a check this week, recent checks), **Sulat** (book library, a 3-step book maker that records a fluent speaker and previews with word highlighting, and a read-along player), and **Settings** (language, text size, privacy and data with delete-all-audio, class roster add/rename, models, about). Sample books without real audio use simulated timing; books you record play your real audio.

Illustrations are Microsoft Fluent Emoji (MIT) in `src/renderer/src/assets/emoji/`. The tamaraw mascot is our own SVG in `components/Tamaraw.tsx`.

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
- **Mock first:** every screen runs on `api/mockApi.ts` fixtures before the engine exists.
- **Color never stands alone:** every label also shows as text or an icon.
- **Design for 1366×768** (common cheap laptops), and check at 1920×1080 for the demo screen.
- **Cross-platform:** no bash-only scripts, `path.join` everywhere, and test on Windows before each demo.
