# Task board

The single source of truth for who does what. `scripts/create_issues.py` turns every unchecked task into a GitHub issue, so **keep the line format exactly**:

```
- [ ] **ID** · Title — owner: <role> · depends: <IDs or none> · done when: <criteria>
```

**Owners:** `ai` (AI engineer) · `backend-1` (engine service) · `backend-2` (data and logic) · `frontend` · `everyone`

**Phases:** finish a phase's gate before relying on it. Work that doesn't depend on the gate continues in parallel.

---

## Phase 0: the aligner test (go/no-go)
Nobody waits on the result. The AI engineer runs the test while everyone else builds things that don't depend on it.

- [ ] **P0-ALL-1** · Record the test set — owner: everyone · depends: none · done when: about 10 passages per language (Filipino, English, one regional language a teammate speaks) are recorded by adults with planted mistakes (swapped, skipped, extra words), stored in `eval/recordings/` (git-ignored), with every mistake logged in `eval/ground_truth.csv`
- [x] **P0-AI-1** · Run the aligner test — owner: ai · depends: P0-ALL-1 · done when: MMS alignment and per-word scores have run on the whole test set, and `eval/REPORT.md` shows mistake-detection precision, recall and F1 per language with a go/no-go call (go if F1 is 0.6 or better)
- [x] **P0-AI-2** · Pin a working PyTorch stack — owner: ai · depends: none · done when: `ai/requirements.txt` pins torch/torchaudio (or transformers) versions that still ship the MMS aligner and forced alignment, and a one-line smoke test aligns a sample file
- [x] **P0-BE1-1** · Engine skeleton — owner: backend-1 · depends: none · done when: a FastAPI app in `engine/` serves `GET /health` and a stub `POST /assess` that returns `docs/api/assess.example.json`
- [x] **P0-BE1-2** · Audio pipeline — owner: backend-1 · depends: P0-BE1-1 · done when: any browser recording (webm, ogg, wav) is converted to a 16 kHz mono WAV with ffmpeg, with a test file covering each input type
- [x] **P0-BE2-1** · Database schema — owner: backend-2 · depends: none · done when: a SQLite schema exists for learners, passages, assessments, word_results, books and practice_attempts, with a script that creates a fresh database
- [ ] **P0-BE2-2** · Seed data — owner: backend-2 · depends: P0-BE2-1 · done when: synthetic learners (no real names) and Filipino and English passages from `data/passages/` load with one command, and the regional passage is added by a teammate who speaks the language
- [ ] **P0-BE2-3** · Group-plan prompt — owner: backend-2 · depends: none · done when: group stats (level, common missed words) turn into a short draft activity in Filipino: an activity template filled with the missed words, plus one example sentence from qwen2.5:7b in Ollama that falls back to the template alone if it fails (English and regional languages later, see `docs/DECISIONS.md`), with 3 saved example outputs in `engine/prompts/examples/` reviewed by a native speaker
- [x] **P0-FE-1** · Desktop scaffold — owner: frontend · depends: none · done when: Electron + Vite + React + TypeScript + Tailwind v4 runs in `desktop/` on Linux and Windows, with design tokens, bundled fonts, the app shell, the status pill and one file holding all UI text (Filipino and English)
- [x] **P0-FE-2** · Browser recorder — owner: frontend · depends: P0-FE-1 · done when: a recorder component captures microphone audio on localhost and uploads it to `/assess`
- [x] **P0-FE-3** · Review screen on mock data — owner: frontend · depends: P0-FE-1 · done when: the screen renders `docs/api/assess.example.json` with color-coded words (each label also shown as text), tap-to-fix, words correct per minute, level, Confirm and Re-record
- [x] **P0-ALL-2** · Go/no-go meeting — owner: everyone · depends: P0-AI-1 · done when: the team has decided between the full plan and the fallback (Whisper for Filipino and English, timing-only checks for IP languages), and the decision is logged in `docs/DECISIONS.md`

## Phase 1: the core Basa flow (record, score, review)

- [x] **P1-AI-1** · Scoring module — owner: ai · depends: P0-AI-1 · done when: `ai.score(audio_path, passage_text)` returns the `words[]` (matched, misread, skipped) and `pauses[]` lists from `docs/API.md` with thresholds tuned on the test set
- [ ] **P1-AI-2** · Whisper fallback (only if the gate is weak) — owner: ai · depends: P0-ALL-2 · done when: Filipino and English passages are scored with Whisper prompted with the passage text, behind the same `score()` interface
- [x] **P1-BE1-1** · Real /assess — owner: backend-1 · depends: P1-AI-1, P0-BE1-2 · done when: `POST /assess` runs the audio pipeline and `ai.score`, returns the contract shape, and logs processing time per request
- [x] **P1-BE1-2** · Audio retention — owner: backend-1 · depends: P1-BE1-1 · done when: a child's audio is deleted when the teacher confirms, unless a keep flag is set, with a test proving the file is gone
- [x] **P1-BE2-1** · Save results and overrides — owner: backend-2 · depends: P0-BE2-1, P1-BE1-1 · done when: assessments and word results are stored, and `PATCH /assessments/{id}/words/{i}` records teacher overrides and recomputes the score
- [x] **P1-BE2-2** · Reading speed and level — owner: backend-2 · depends: P1-BE2-1 · done when: words correct per minute and a reading level are computed from final (overridden) results, with level names checked against DepEd's current CRLA profiles
- [ ] **P1-BE2-3** · Demo checks seed — owner: backend-2 · depends: P1-BE2-2 · done when: `python -m app.seed --demo` loads confirmed demo checks from `data/demo_checks/` (PR #16) mapped to the synthetic learners, with every reading level and at least one before-and-after pair shown, ids prefixed `demo_` and hand-edited checks documented as synthetic
- [ ] **P1-FE-1** · Review screen on the real API — owner: frontend · depends: P0-FE-3, P1-BE1-1 · done when: the review screen works end-to-end against the engine, including overrides and confirmation
- [ ] **P1-FE-2** · Learner and passage pickers — owner: frontend · depends: P0-BE2-2 · done when: the teacher can pick a learner and a passage before recording

## Phase 2: complete the loop (Sulat, Sanay, class view)

- [ ] **P2-AI-1** · Word timings for a model reading — owner: ai · depends: P1-AI-1 · done when: a fluent speaker's correct reading yields start and end times for every word, checked by ear on 3 recordings
- [ ] **P2-AI-2** · Single-word check — owner: ai · depends: P1-AI-1 · done when: `ai.check_word(audio_path, word)` returns a match or no-match result for Sanay's "Say it"
- [ ] **P2-BE1-1** · Sulat alignment endpoint — owner: backend-1 · depends: P2-AI-1 · done when: `POST /books` stores a story, its model reading and word timings
- [ ] **P2-BE1-2** · Word clips — owner: backend-1 · depends: P2-BE1-1 · done when: `GET /books/{id}/clips/{i}` returns that word's audio cut from the model reading
- [ ] **P2-BE2-1** · Practice-set builder — owner: backend-2 · depends: P1-BE2-1 · done when: `GET /learners/{id}/practice` returns the child's missed words from their latest check, each with its sentence and clip
- [ ] **P2-BE2-2** · Progress tracking — owner: backend-2 · depends: P2-BE2-1 · done when: `GET /learners/{id}/progress` compares two checks word by word and returns the change in reading speed
- [ ] **P2-BE2-3** · Class view data, plans and export — owner: backend-2 · depends: P0-BE2-3, P1-BE2-2 · done when: `GET /class` returns learners grouped by level with an Ollama draft plan per group, and `GET /class/export.csv` downloads results
- [ ] **P2-FE-1** · Sanay practice screen — owner: frontend · depends: P2-BE2-1, P2-BE1-2 · done when: a child can Hear it, Say it (with a try-again or got-it result) and reread the sentence for each missed word
- [ ] **P2-FE-2** · Sulat book maker and player — owner: frontend · depends: P2-BE1-1 · done when: a teacher can type a story and record a model reading, and playback highlights each word as it's spoken
- [ ] **P2-FE-3** · Class view — owner: frontend · depends: P2-BE2-3 · done when: groups, counts and draft plans are shown, with per-learner progress

## Phase 3: numbers, polish and submission

- [ ] **P3-AI-1** · Accuracy and speed report — owner: ai · depends: P1-AI-1 · done when: `eval/REPORT.md` has precision, recall and F1 per language, reading-speed error versus a human scorer, and CPU processing time and memory on our laptops
- [ ] **P3-AI-2** · Model disclosures — owner: ai · depends: none · done when: every model's name, version, license (MMS is CC-BY-NC-4.0) and source is listed in the README
- [ ] **P3-BE1-1** · One-command offline start — owner: backend-1 · depends: P1-BE1-1 · done when: `scripts/start.sh` starts the engine, Ollama and the web app with models already downloaded, and a separate script downloads all models once
- [ ] **P3-BE1-2** · Airplane-mode run — owner: backend-1 · depends: P3-BE1-1 · done when: the full Sulat, Basa, Sanay flow works with Wi-Fi off on a clean laptop
- [ ] **P3-BE2-1** · README for judges — owner: backend-2 · depends: P3-AI-2 · done when: the README covers setup, "why does this benefit from running locally?", what runs locally versus what needs internet, and disclosures
- [ ] **P3-FE-1** · Demo polish — owner: frontend · depends: P2-FE-1 · done when: fonts are self-hosted (no internet needed), Filipino copy has been reviewed by a native speaker, and the demo path has no rough edges
- [ ] **P3-FE-2** · Backup demo video — owner: frontend · depends: P3-BE1-2 · done when: a recording of the full demo run is saved and ready on a second tab
- [ ] **P3-ALL-1** · Measure the time saving — owner: everyone · depends: P1-FE-1 · done when: a teammate has scored the same readings by hand and with Basa, and the measured difference replaces "in seconds" in the pitch
- [ ] **P3-ALL-2** · Teacher outreach — owner: everyone · depends: none · done when: at least one public-school teacher has given a quote or feedback, or public teacher posts about CRLA are collected with links
- [ ] **P3-ALL-3** · Rehearse the demo — owner: everyone · depends: P3-BE1-2 · done when: the demo in `docs/DEMO.md` has been run end-to-end three times without a fix
- [ ] **P3-ALL-4** · Submit — owner: everyone · depends: P3-BE2-1, P3-FE-2 · done when: name, description, team, public GitHub repo, demo video, X/LinkedIn video URL, local-versus-internet statement, disclosures and the "why local" answer are all submitted
