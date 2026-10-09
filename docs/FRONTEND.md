# Frontend design: Basa at Sulat (desktop, Windows + Linux)

## Context
The **frontend** (owner: frontend developer) is everything the teacher and child see. The backend team builds the local Python engine (FastAPI on `127.0.0.1`).

The app is a **local-AI desktop app** that has to run on **Windows and Linux** and look polished enough for a top-10 hackathon demo. Two scoring criteria depend directly on the frontend:
- **Demo Quality (15%)**
- **Local AI Implementation (25%)**: the interface should make "this runs on your machine" visible

Frontend work is defined by `docs/API.md` (the contract) and the mockups in the team deck. This doc covers only the frontend scope: the shell, screens, components, visual system, states and build order.

## 1. Frontend stack
| Choice | Pick | Why |
|---|---|---|
| Desktop shell | **Electron** via `electron-vite` | Identical Chromium on Windows and Linux, so microphone recording and rendering behave the same. Tauri's Linux webview blocks the microphone unless the app adds a custom handler. |
| Interface | React + TypeScript + **Vite** | No server needed; simpler than Next.js inside a desktop shell. |
| Styling | **Tailwind v4** (`@tailwindcss/vite`, tokens in `@theme`, no config file) | Fast to build, and design tokens live in one CSS file. |
| Building blocks | Radix UI (Dialog, Popover, Tooltip, Tabs, Toast) + lucide-react | Accessible, unstyled primitives. |
| Data | TanStack Query + one typed `api.ts` | Caching, loading and error states for free. Easy to swap mock ↔ real. |
| Navigation | React Router (memory router) | No URL bar in a desktop app. |
| Fonts | `@fontsource/domine`, `@fontsource/nunito-sans` | Bundled, so they work offline. Same look as the deck. |
| Audio | MediaRecorder (webm/opus) + Web Audio `AnalyserNode` for the live waveform | Built into Chromium on both operating systems. |

**Frontend-owned Electron main process (small):** open the window (minimum 1280×720), allow the microphone for our own page only, block navigation to the outside, start the engine with a free port and pass the port to the interface through preload, and stop the engine on quit. Backend 1 provides the engine start command; the main process just calls it.

## 2. Mock-first workflow (never blocked on the backend)
- `src/renderer/api/` holds one interface with **two implementations**: `mockApi` (reads `docs/api/assess.example.json` plus fixtures, with fake delays) and `httpApi` (the real engine).
- A switch picks between them: `VITE_API=mock|real`, or automatically "mock if the engine isn't reachable" in dev.
- Fixtures cover every state: a perfect reading, many mistakes, a silent recording, an engine error, and a slow response (to test loading).
- **Result:** every screen gets built and polished before the backend exists, and swapping to real is one setting.

## 3. Information architecture
**Teacher mode** has a sidebar with:
- **Klase** (Class): home
- **Basa** (Check)
- **Sulat** (Books)
- **Settings**

**Kid mode** is full-screen practice (Sanay). The teacher exits by holding a corner button for 2 seconds.

```
First run (model and mic check) → Class
Class → Learner → [Check | Start practice]
Check: pick learner → pick passage → Record → Processing → Review → Confirm → (Practice?)
Practice (kid mode): word 1..n → reread → done → back to Learner (progress shown)
Books: list → new book (type story → record model reading → preview) → use as passage
```

## 4. Screen specs (designed for 1366×768, the common cheap-laptop size)
1. **First run / system check:** a checklist of local parts: aligner model (with size on disk), Ollama, microphone test with a live level meter. Copy: "Everything runs on this laptop. No account. No internet needed." Each failure gets a fix-it card (e.g. "Windows: Settings → Privacy → Microphone → allow desktop apps").
2. **Class (home):** learner cards grouped by reading level (each level shown as color plus text), last check date, "needs practice" badge, and a draft plan per group (collapsible; "plans unavailable" if Ollama is off). Empty state: "Add learners" with a sample class button.
3. **Check: setup:** searchable learner list, then passage cards (language tag, grade, word count).
4. **Check: record:** the passage in large type (32–36px), a big Record button (space bar toggles), a live waveform, a timer, a Stop button, and "Recording stays on this laptop."
5. **Check: processing:** staged steps ("Preparing audio → Lining up words → Scoring"), honest and short. If it takes more than 10 seconds: "Still working… older laptops can take longer."
6. **Check: review (the hero screen):**
   - Words reveal one by one with their label. Each label is color + icon + text: matched (no fill), misread (orange fill + "misread"), skipped (dashed outline + "skipped"), pause marker (⏸ 1.8 s between words).
   - Tapping a word opens a popover: Correct / Misread / Skipped, plus "play this part" (replays the clip if audio is still kept).
   - Side panel: big words-correct-per-minute number, level chip, "2 words need your check", **"Scored in 2.1 s on this laptop's CPU"**, then Confirm and Re-record.
   - After Confirm: toast "Saved · audio deleted ✓", plus "Start practice for Lina".
7. **Learner:** words-correct-per-minute trend (small line chart), check history, per-word progress (misread → correct), and "Start practice."
8. **Practice (kid mode):**
   - The word in 120px type, a big **Hear it** button (speaker's voice) and a big **Say it** button (records about 2 seconds).
   - Result: "Try again" (gentle shake) or "Got it!" (burst animation plus a chime).
   - After the words: reread the sentence with the word highlighted, then a "Done" screen with stars.
   - Almost no text, audio first, every button at least 96px.
9. **Books (Sulat):** library grid. New book: title, language, text area → record a model reading → **karaoke preview** (words light up in time with the audio) → Save → "Use as passage."
10. **Settings / Privacy:** language (Filipino/English), "delete all audio now", data folder location, the models and licenses list (the disclosures, shown in-app), export CSV, an About page.

**Every data screen has designed states:** loading (skeletons), empty, error (with a retry and a plain-language reason), and offline-engine ("Starting the local engine…").

## 5. Making local AI visible (aimed at the Local AI score)
- **A persistent status pill** in the sidebar footer: "On this device · Internet not needed", with dots for the aligner, Ollama and the microphone. Click for details.
- **Honest timing** on every result, from the engine's `timings` (ask Backend 1 to add this to `/assess`).
- **Privacy moments:** "audio deleted ✓", "nothing leaves this laptop".
- The airplane-mode demo just works: the pill never shows "offline" as an error.

## 6. Visual system
- **Tokens** (CSS variables in `@theme`, matching the deck):

  | Token | Value |
  |---|---|
  | ink | `#1E2740` |
  | ink-2 | `#26314F` |
  | paper | `#FAF6EE` |
  | paper-2 | `#F1EADB` |
  | accent | `#B4521A` |
  | accent-light | `#F0A35E` |
  | correct | `#1F6F6B` |
  | correct-bg | `#E3F1EF` |
  | misread-bg | `#FBE3CF` |
  | muted | `#6B7280` |

- **Type:** Domine for headings and the kid-mode word, Nunito Sans for interface text. Scale: 14 / 16 / 20 / 28 / 36 / 56 / 120.
- **Shape:** 12px radius on cards and 999px on chips; one soft shadow level.
- **Accessibility:** status is never shown by color alone; 4.5:1 contrast; full keyboard use in teacher mode (space = record, Enter = confirm, arrows to move between words); `prefers-reduced-motion` respected.
- **Motion:** word reveal (about 40ms stagger), waveform, "got it" burst. Nothing longer than 400ms in teacher mode.
- **Light theme only** for this release.
- **Language:** all UI text lives in one `strings.ts` with Filipino and English. Default: Filipino with English labels where clearer.

## 7. Component inventory
- **Layout:** `AppShell`, `Sidebar`, `StatusPill`, `KidModeShell` (with hold-to-exit)
- **Reading:** `PassageText`, `WordChip` (label, selected, onFix), `WordFixPopover`, `PauseMarker`, `KaraokeText` (highlights by timings)
- **Audio:** `RecordButton`, `LiveWaveform`, `MicLevelMeter`, `AudioPlayer` (clip / full)
- **Results:** `ScorePanel` (words correct per minute, level, timing), `LevelChip`, `ProgressTable`, `TrendChart` (a small SVG, no chart library)
- **States:** `Skeleton`, `EmptyState`, `ErrorState`, `EngineStarting`
- **Practice:** `BigWordCard`, `HearItButton`, `SayItButton`, `ResultBurst`

## 8. Folder structure (`desktop/`)
```
desktop/
  src/main/        window, mic permission, engine launcher (calls Backend 1's command)
  src/preload/     exposes { enginePort, platform } safely
  src/renderer/
    app/           routes, AppShell, providers (QueryClient, router)
    screens/       FirstRun, Class, CheckSetup, CheckRecord, CheckReview, Learner, Practice, Books, Settings
    components/    the inventory above
    api/           types.ts (mirrors docs/API.md), mockApi.ts, httpApi.ts, fixtures/
    audio/         useRecorder, useWaveform
    styles/        app.css (@import "tailwindcss"; @theme tokens; fonts)
    strings.ts
```

## 9. Build order (maps to frontend tasks in docs/TASKS.md)
1. **P0-FE-1:** scaffold electron-vite + React + TS + Tailwind v4, tokens, fonts, AppShell, StatusPill (mock). Runs on Linux, and a teammate confirms on Windows.
2. **P0-FE-2:** `useRecorder` + `LiveWaveform` + `RecordButton`; save the recording to disk in dev to confirm audio quality.
3. **P0-FE-3:** the review screen on mock data, polished. This is the hero of the demo, so it gets the most love.
4. Check setup and processing screens; First run on mock data.
5. **P1-FE-1:** switch to `httpApi` when Backend 1's `/assess` is live; overrides and confirm.
6. **P1-FE-2:** learner and passage pickers on real data.
7. **P2-FE-1:** kid mode + Practice. **P2-FE-2:** Books + karaoke. **P2-FE-3:** Class view + Learner trend.
8. **P3-FE-1:** polish pass (motion, empty and error states, Filipino copy reviewed by a native speaker). **P3-FE-2:** record the backup demo video.

## 10. What the frontend needs from the backend team (contract asks)
- `/assess` response adds `timings: {convert_ms, align_ms, score_ms}` for the honest-timing line.
- `GET /health` returns `{aligner, ollama}` status for the status pill and First run.
- An engine start command the Electron main process can call: `python -m engine --port <n> --data-dir <path>`, plus `POST /shutdown` (Windows doesn't kill child processes cleanly).
- Clip endpoints for Practice and Books (already in API.md: `/books/{id}/clips/{i}`).
- Frontend proposes these as a small PR to `docs/API.md`, per our rule of changing the contract first.

## Verification
- `npm run dev` in `desktop/` opens the app on **Linux** and on **a teammate's Windows laptop**: the microphone records, the waveform moves, and mock results render.
- Click through every screen with every fixture (perfect, many mistakes, silent, error, slow), so every state looks designed.
- Keyboard-only run of the Check flow; check contrast with devtools; turn on reduced motion and confirm animations calm down.
- At 1366×768 nothing overflows; also check at 1920×1080 on the HDMI screen for the demo.
- With airplane mode on, the app opens with fonts, icons and mock data all working (proves nothing loads from the internet).
- `npm run typecheck` and `npm run build` pass on both operating systems.
