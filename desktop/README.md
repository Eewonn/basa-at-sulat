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

**Clickable flow today:** Klase → Basahin (pick a passage, record with a live waveform) → processing stages → Resulta (tap a word to fix it, I-confirm) → Sanay kid mode (Pakinggan / Sabihin, reread, done). Pakinggan and the Sabihin result are simulated until the engine exists.

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
