# engine/: local API service (FastAPI)

**Owners:** Backend 1 (engine service) and Backend 2 (data and logic) · **Contract:** [../docs/API.md](../docs/API.md)

## Who builds what
| Backend 1: audio in, results out | Backend 2: data and logic |
|---|---|
| App skeleton, `/health` (P0-BE1-1) | SQLite schema and setup script (P0-BE2-1) |
| Audio pipeline: anything → 16 kHz mono WAV via ffmpeg (P0-BE1-2) | Seed learners and passages (P0-BE2-2) |
| `/assess` calling `ai.score` (P1-BE1-1) | Save results, teacher overrides (P1-BE2-1) |
| Delete audio on confirm (P1-BE1-2) | Reading speed and level (P1-BE2-2) |
| `/books` for Sulat timings (P2-BE1-1) | Sanay practice sets, progress (P2-BE2-1/2) |
| `/books/{id}/clips/{i}` word clips (P2-BE1-2) | Class view, Ollama plans, CSV export (P2-BE2-3) |
| One-command offline start (P3-BE1-1) | README for judges (P3-BE2-1) |

## Suggested layout
```
engine/
  app/main.py          FastAPI app and routers
  app/audio.py         ffmpeg conversion (Backend 1)
  app/db.py            SQLite access (Backend 2)
  app/levels.py        reading speed and level (Backend 2)
  app/plans.py         Ollama group plans (Backend 2)
  prompts/             prompt templates and saved example outputs
  storage/             audio and books at runtime (git-ignored)
```

## Rules
- Runs on `localhost:8000`. The web app calls it directly, and nothing calls out to the internet.
- Learner names are synthetic or initials only.
- A child's audio is deleted when the teacher confirms, unless keep-audio is set.

## Status and handoff (Backend 1)

**Done (Phase 0):** P0-BE1-1 engine skeleton and P0-BE1-2 audio pipeline.

**Run it**
```
cd engine
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest                      # needs ffmpeg and ffprobe installed
.venv/bin/uvicorn app.main:app --port 8000
```

**What exists**
- `GET /health` reports `aligner: not_loaded`, `ollama: unknown` until real models are wired in.
- `POST /assess` is a stub: it needs `audio`, `passage_id` and `learner_id`, and returns `docs/api/assess.example.json` unchanged.
- `app/audio.py`: `convert_to_wav16k(src, dst)` turns webm/ogg/wav into 16 kHz mono WAV. It is not called by `/assess` yet. Tests use synthetic audio, not real browser recordings.

**Phase 1 (Backend 1) is blocked, and starts when:**
- **P1-AI-1** (`ai.score(audio_path, passage_text)`) exists. It needs P0-AI-1 (aligner test) and P0-ALL-1 (recorded test set).
- The Phase 0 go/no-go (P0-ALL-2) has chosen MMS or the Whisper fallback. Both sit behind the same `score()` interface, so the engine work is the same either way.

Then Backend 1 does **P1-BE1-1** (real `/assess`: convert audio, call `ai.score`, log processing time) and **P1-BE1-2** (delete audio on confirm).

**Needs agreeing with Backend 2 before P1-BE1-2:** who owns the assessments store and the `POST /assessments/{id}/confirm` handler. Backend 2's P1-BE2-1 stores assessments, and audio deletion hooks into confirm.

**AI engineer:** please tell Backend 1 when `ai.score` lands on a branch.

## Update: real /assess (P1-BE1-1)
`POST /assess` now validates the passage and learner against the database, converts the upload to 16 kHz mono WAV, calls `ai.score(wav, passage_text)`, and returns the contract shape plus `timings`. It logs the per-request processing time (`engine.assess` logger). The converted WAV is kept at `engine/storage/audio/<assessment_id>.wav` (git-ignored) for the confirm step (P1-BE1-2).

- `ai.score` is still the stub from #4 (every word "matched"). The route needs no change when the real scorer lands.
- `wcpm` and `level` are `null` until Backend 2's P1-BE2-2. Results are **not** saved by `/assess`; storing them is P1-BE2-1.
- Start with `python -m app` from `engine/`. Port is `$PORT`, default 8000. Tests need ffmpeg.

## Update: robustness (while Backend 2 finishes P1-BE2-1)
- `/assess` returns `503` if the scoring model isn't installed and `500` if scoring fails; either way the converted WAV is deleted and the engine keeps running.
- `GET /health` reports `aligner: loaded` once the model is in memory.
- `BASA_WARM_UP=1 python -m app` loads the aligner at startup (about 10 s; needs `ai/requirements.txt` and the weights). It is off by default, so tests and machines without torch are unaffected. If warm-up fails the engine still starts.
- `delete_audio(audio_path)` in `app/audio.py` deletes a recording (path relative to `engine/storage/`; a missing file is fine; paths outside `engine/storage/` are refused). Backend 2's confirm route will call it.
- Tests replace `score`, so they never load the 1.2 GB model.

## Status and handoff (Backend 2)

### Results and overrides (P1-BE2-1)
Built against `docs/api/assess.example.json`, ahead of the real `/assess`.

**What exists**
- `app/assessments.py` is the assessments store. Functions take a connection from `app.db.connect()` and return the API shape:
  - `save_assessment(conn, result, audio_path=None)` stores an `/assess` result as a draft in one transaction. It checks the learner and passage exist and that every word sits at its index in the passage, and raises `InvalidAssessmentError` otherwise.
  - `get_assessment(conn, id)` returns the stored check.
  - `override_word(conn, id, i, label)` saves the teacher's label and recomputes the score.
  - `confirm_assessment(conn, id, keep_audio=False)` marks a draft as final.
- `PATCH /assessments/{id}/words/{i}` lives in `app/routes/assessments.py`, wired into `main.py` with one `include_router` line. Error codes are in `docs/API.md`.
- `app/levels.py` computes `wcpm` from the final labels. **`level` is always `None` (null in the API) until P1-BE2-2.**

**For Backend 1**
- **P1-BE1-1:** after `ai.score`, call `save_assessment(conn, result, audio_path=...)` and return what it gives back. It ignores any `wcpm`/`level` in the result and computes them itself.
- **P1-BE1-2 (proposed split for confirm, needs Backend 1's OK):** Backend 2 owns the data side, `confirm_assessment()`. Backend 1 owns the `POST /assessments/{id}/confirm` route and the audio. Call `confirm_assessment()` first and delete the file only if it succeeds: it raises `AssessmentNotFoundError` (404) or `AssessmentConfirmedError` (409). Then clear `audio_path` unless `keep_audio` is set. `confirm_assessment()` doesn't touch the file or `audio_path`.

### Group plans (P0-BE2-3)
`app/plans.py` turns one group's stats into a draft activity in Filipino. The activity is a template from `prompts/activities-fil.json` filled with the group's missed words. **qwen2.5:7b** in Ollama adds one example sentence (`prompts/sentence-fil.txt`, or `prompts/sentence-small-words-fil.txt` when every missed word is a function word like *ng* or *sa*). The sentence is checked and retried with up to 3 seeds; if it still fails, the plan is the template alone. See `docs/DECISIONS.md` for why, and for the license (Apache 2.0).

**One-time setup, while online:** install Ollama from ollama.com, then run `ollama pull qwen2.5:7b` (about 4.7 GB; it needs about 5 GB of free RAM while running).

**Regenerate the saved examples** (`prompts/examples/example-1.md` to `-3.md`, from `prompts/examples/inputs.json`):
```
cd engine
python -m app.plan_examples
```
It writes nothing unless every word group gets a model sentence (here, unlike in the app, a fallback is an error). After regenerating, a native Filipino speaker fills in the review section of each file.

**For P2-BE2-3:** `generate_plan(GroupStats(level, learner_count, common_missed_words))` returns the `draft_plan` string. Model problems (Ollama not running, model not pulled, timeout, every sentence rejected) never raise: the plan comes back as the template alone and the reason is logged as a warning. It raises `PlanError` only for bad input (unsupported language, empty level, bad learner count) or a broken template file. `generate_plan_result` returns the same text plus how it was made (`fallback_reason`, `tries`, Ollama's timings).

| Setting | Default |
|---|---|
| `OLLAMA_MODEL` | `qwen2.5:7b` |
| `OLLAMA_URL` | `http://127.0.0.1:11434` |
| `OLLAMA_TIMEOUT` | `120` seconds |

## Update: audio retention (P1-BE1-2)
- `/assess` now saves the result with Backend 2's `save_assessment` (so `wcpm` is real; `level` stays `null` until P1-BE2-2) and stores `audio_path` as `audio/<assessment_id>.wav`, relative to `engine/storage/`. If saving fails, the WAV is deleted.
- `POST /assessments/{id}/confirm` (`app/retention.py`) calls `confirm_assessment`, then `delete_audio`, then sets `audio_path` to `NULL`. `{"keep_audio": true}` keeps the file and the path.
- If the delete fails, the row is still confirmed and `audio_path` stays set, so `status='confirmed' AND keep_audio=0 AND audio_path IS NOT NULL` lists the deletions still owed. **The engine retries them each time it starts** (`delete_owed_audio()` in `app/retention.py`, called from the startup hook): it deletes the file, clears `audio_path`, and logs any that still fail. It never touches drafts or kept recordings, and it never stops the engine from starting. It runs only at startup, so an engine left running for days won't retry until the next restart.
- Backend 2 had planned to own the confirm route; her merged docstring assigned it to Backend 1, so it lives here. Her `confirm_assessment` is unchanged.
- `/assess` uses the same database guard as the assessments routes (`get_conn`): with no database it returns `503` and creates no file, and it uses one connection per request for the lookups and the save.
