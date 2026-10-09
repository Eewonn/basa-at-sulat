# Offline start: manual checklist

The tests for `scripts/` and the engine command line need no internet, Ollama, `torch` or weights, so they use stubs and fakes. They cannot prove the items below. Run this on a laptop that has everything installed, and tick it for P3-BE1-1 and P3-BE1-2.

## P3-BE1-1: one-command start (with internet once)
- [ ] `pip install -r engine/requirements.txt -r ai/requirements.txt` finishes (torch 2.8 is pinned; it was verified on Python 3.13 / Windows 11, not 3.14).
- [ ] `cd desktop && npm install` finishes.
- [ ] Ollama is installed and running.
- [ ] `python scripts/download_models.py` downloads the aligner (about 1.2 GB into `models/torch/`) and pulls `qwen2.5:7b`. Running it again says "already downloaded" for both.
- [ ] `scripts/start.sh --check` shows no `[MISSING]` item.
- [ ] `scripts/start.sh` opens the desktop app, the status pill shows the aligner as loaded, and a first reading is scored (the first start takes longer while the aligner loads).
- [ ] **The app's screens show data from the engine, not mock data.** Open the app that `start.sh` launched and check that the learner and passage lists come from the database. A browser enforces CORS and the automated tests do not run one, so this is the only check that proves the page can call the engine.
- [ ] Closing the app leaves no `python -m app` and no `ollama serve` that `start.sh` started (check the process list).
- [ ] A fresh clone gets a database with the synthetic learners and passages on its first start.

## P3-BE1-2: airplane-mode run (Wi-Fi off, clean laptop)

Goal (TASKS.md): the full Sulat, Basa, Sanay flow works with Wi-Fi off on a clean laptop. Tick the box only after every step below passes, or fails only on a step that is marked "skip if".

### Before the run: automated proof (on the dev laptop, any time)
These show the code never reaches the internet. They do not replace the run.
- `python scripts/offline_audit.py` finds no outbound URL and no network client library in `engine/app`, `ai` or `scripts`.
- `cd engine && pytest` and `cd scripts && pytest` pass with a guard that refuses any connection that leaves the laptop (`scripts/netguard.py`). It covers code that runs inside the test process; the tests that start the engine or the launcher as separate processes are covered by the URL scan only.

### Clean laptop setup (internet allowed for this part only)
- [ ] Clone the repo, install Python 3, Node.js, ffmpeg and Ollama.
- [ ] `pip install -r engine/requirements.txt -r ai/requirements.txt`, `cd desktop && npm install`.
- [ ] `python scripts/download_models.py`, then `scripts/start.sh --check` shows no `[MISSING]` item.
- [ ] Start Ollama once so its model is in place, then close the app and everything it started.

### The offline run
- [ ] Turn Wi-Fi off and unplug any cable. Show that it is off (system tray). Leave it off for the whole run.
- [ ] `scripts/start.sh` starts the engine and the app with no network error, and the pill shows the aligner as loaded.
- [ ] The app's screens show data from the engine, not mock data (learner and passage lists come from the database).
- [ ] **Sulat:** make a book from a short story and a model reading read by a fluent speaker; playback highlights each word as it is spoken.
- [ ] **Basa, Filipino:** a teammate reads `fil_g2_01` with two planted mistakes (skip "ng", say "pala" for "palay"). Both are flagged. Tap one to override, then confirm. The child's audio file under `engine/storage/audio/` is gone after confirm.
- [ ] **Basa, English:** read `eng_g2_01` and review the result.
- [ ] **Basa, regional language** (skip if no regional passage is seeded yet: today only `fil` and `eng` passages exist). Record it as "skipped" in the table.
- [ ] **Sanay:** open the learner's practice set. "Hear it" plays the word's clip, "Say it" gives a result, and the progress panel updates.
- [ ] **Class view:** groups by level and a draft plan for each group (a template sentence is fine if Ollama is not running).
- [ ] No screen shows an error because the network is off.
- [ ] Close the app. No `python -m app` and no `ollama serve` that `start.sh` started is left running.
- [ ] Repeat the run on a second clean laptop (or after a reboot of the first).

### Results
Fill in one row per run. Say "skipped" for a step that was skipped, and never leave a step out.

| Date | Run | Laptop / OS | Who | Result | Notes (steps skipped or failed) |
|---|---|---|---|---|---|
| 2026-10-10 | P3-BE1-1 (one-command start) | not recorded | Backend-1 | Signed off by Backend-1 | Per-step details were not recorded. The reviewer ran `start.sh` for real on a laptop with ffmpeg, npm, `torch` and the weights, but no Ollama. |
| | P3-BE1-2 (airplane mode) | | | not run yet | Needs the frontend screens (P1-FE, P2-FE) and a clean laptop. |
