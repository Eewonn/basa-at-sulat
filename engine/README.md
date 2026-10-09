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
