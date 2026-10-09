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
