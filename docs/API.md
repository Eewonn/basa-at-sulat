# API contract

The app talks to the engine (`engine/`, FastAPI) on `http://localhost:8000` by default. Set the `PORT` environment variable to use another port (the desktop app picks a free one). Start it from `engine/` with `python -m app`. **Change this file first, tell the team, then change code.** Frontend builds against [`api/assess.example.json`](api/assess.example.json) until the real endpoint exists.

## Word labels

| `label` | Meaning |
|---|---|
| `matched` | The sound fits the word's letters |
| `misread` | Weak match: likely said something else |
| `skipped` | Almost no time on the word, or no match |

Hesitations aren't a word label: they're reported in `pauses` (`before_word` index plus `seconds`), because a child can pause and then read the word correctly.

`score` is 0–1 (higher means a better match). `start`/`end` are seconds into the recording, and can be `null` when the scorer found no timing for a word (for example, a skipped one).

`wcpm` (words correct per minute) is a whole number: `matched` words ÷ the recording's minutes, computed by the engine from the final labels, so it follows teacher overrides. `level` is one of `Low Emerging`, `High Emerging`, `Developing`, `Transitioning`, `At Grade Level` (lowest first), computed from accuracy and `wcpm` and also following overrides. **It is an estimate from reading fluency, not an official CRLA profile**, because the app asks no comprehension questions. Label it that way in the UI (for example "Estimated level"). See `docs/DECISIONS.md` for the rules. Clients should still handle `null` for both fields: `/assess` returns `null` until it saves its result (P1-BE1-1).

## Basa: checks

### `POST /assess`
Multipart form: `audio` (webm, ogg or wav), `passage_id`, `learner_id`.
Returns:

```json
{
  "assessment_id": "a_123",
  "learner_id": "l_07",
  "passage_id": "fil_g2_01",
  "duration_sec": 41.2,
  "words": [
    {"i": 0, "text": "Nagtanim", "label": "matched", "score": 0.91, "start": 0.42, "end": 1.10},
    {"i": 3, "text": "ng", "label": "skipped", "score": 0.08, "start": 3.60, "end": 3.64},
    {"i": 4, "text": "palay", "label": "misread", "score": 0.31, "start": 3.70, "end": 4.30}
  ],
  "pauses": [{"before_word": 3, "seconds": 1.8}],
  "wcpm": 52,
  "level": "Developing",
  "status": "draft",
  "timings": {"convert_ms": 180, "align_ms": 2400, "score_ms": 35}
}
```

`timings` is the processing time on this laptop, for the "scored in X s" line. Until `ai.score` reports alignment and scoring separately, `align_ms` covers the whole `ai.score` call and `score_ms` is `0`. `wcpm` and `level` are `null` until `/assess` saves its result through Backend 2's store, which computes both.

Errors: `400` if the audio can't be read, `404` for an unknown `passage_id` or `learner_id`, `422` if a field is missing, `503` if the scoring model isn't installed on this engine, `500` if scoring fails. Scoring can take a while (about 0.6× the recording length on CPU, plus ~10 s for the first call unless the engine was started with `BASA_WARM_UP=1`), so the app should wait and show a progress state.

### `PATCH /assessments/{id}/words/{i}`
Body `{"label": "matched"}`. This is the teacher's override, and it returns the updated assessment (recomputed `wcpm`, `level`). Setting a word back to the AI's original label undoes the override.

Errors (body `{"detail": "<what went wrong>"}`):

| Status | When |
|---|---|
| `404` | No assessment with that id, or it has no word `i` |
| `409` | The assessment is already confirmed, so its results are final |
| `422` | `label` isn't `matched`, `misread` or `skipped`, or `i` isn't a whole number from 0 |
| `503` | The engine has no database yet (run `python -m app.seed` in `engine/`) |

### `POST /assessments/{id}/confirm`
Marks the assessment final (`status: "confirmed"`) and deletes the audio unless `{"keep_audio": true}`.

## Learners and passages
- `GET /learners` → `[{"id", "display_name", "grade"}]` (display names are synthetic or initials only)
- `GET /passages` → `[{"id", "title", "language", "grade", "text"}]`

## Sulat: books
- `POST /books`: multipart form with `title`, `language`, `text` and `audio` (the model reading). Returns `{"id", "words": [{"i", "text", "start", "end"}]}`
- `GET /books/{id}` → the book with word timings
- `GET /books/{id}/audio` → the full model reading
- `GET /books/{id}/clips/{i}` → audio for word `i` only

## Sanay: practice
- `GET /learners/{id}/practice` → `{"items": [{"word", "sentence", "book_id", "word_index"}]}`, built from the child's latest confirmed check
- `POST /practice/check`: multipart form with `audio` and `word`. Returns `{"word", "result": "match" | "no_match", "score"}`
- `GET /learners/{id}/progress` → `{"checks": [...], "words": [{"text", "before", "after"}], "wcpm_before", "wcpm_after"}`

## Class view
- `GET /class` → `{"groups": [{"level", "learner_ids", "common_missed_words", "draft_plan"}]}`
- `GET /class/export.csv`

## Proposed by frontend (needs team agreement)
These support the learner profile and story categories. Until the engine implements them, the app uses sample data for them.
- `category` on every passage: `"bukid" | "pamilya" | "hayop" | "kalikasan" | "paaralan"`
- `GET /learners` items also include `stars`, `streak_days` and `latest_wcpm` (for the class summary cards)
- `GET /learners/{id}/stats` → `{"stars", "streak_days", "minutes_read", "wcpm_history": [{"date", "wcpm"}], "practicing": ["palay", ...]}`
  - stars = words gotten right in Sanay; streak = consecutive days with a check or practice; minutes = recording time
- `POST /practice/check` also takes `learner_id`, so a correct word can earn a star

## Health
- `GET /health` → `{"ok": true, "models": {"aligner": "loaded", "ollama": "up"}}`
  - `models.aligner` is `loaded` or `not_loaded`; `models.ollama` is `up`, `down` or `unknown`. The engine reports `not_loaded` until the aligner is in memory (after the first `/assess`, or at startup with `BASA_WARM_UP=1`), and `unknown` for Ollama until it is wired in.

## Contract changes

### 2026-10-10 · backend-2 (P1-BE2-2)
- `level` is now computed for every saved check. It is one of `Low Emerging`, `High Emerging`, `Developing`, `Transitioning`, `At Grade Level`. It is a **fluency-based estimate** using CRLA's names, not an official CRLA result (see `docs/DECISIONS.md`).
- An override can change `level` as well as `wcpm`.
- **Frontend:** show it as an estimate, map the five names to colors, and keep handling `null` (from `/assess` until it saves).

### 2026-10-10 · backend-2 (P1-BE2-1)
- `PATCH /assessments/{id}/words/{i}` now lists its error responses (404, 409, 422, 503).
- `level` is `null` until P1-BE2-2. **Frontend:** `desktop/src/renderer/src/api/types.ts` types it as `string`; it should be `string | null`.
- `wcpm` is defined (whole number, `matched` words per minute, from the final labels).
- `start`/`end` can be `null` for a word with no timing (the database already allowed this). **Frontend:** `Word.start`/`Word.end` should be `number | null`.
