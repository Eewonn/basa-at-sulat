# API contract

The web app talks to the engine (`engine/`, FastAPI) on `http://localhost:8000`. **Change this file first, tell the team, then change code.** Frontend builds against [`api/assess.example.json`](api/assess.example.json) until the real endpoint exists.

## Word labels

| `label` | Meaning |
|---|---|
| `matched` | The sound fits the word's letters |
| `misread` | Weak match: likely said something else |
| `skipped` | Almost no time on the word, or no match |

Hesitations aren't a word label: they're reported in `pauses` (`before_word` index plus `seconds`), because a child can pause and then read the word correctly.

`score` is 0–1 (higher means a better match). `start`/`end` are seconds into the recording.

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
  "status": "draft"
}
```

### `PATCH /assessments/{id}/words/{i}`
Body `{"label": "matched"}`. This is the teacher's override, and it returns the updated assessment (recomputed `wcpm`, `level`).

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
- `/assess` response includes `timings: {"convert_ms", "align_ms", "score_ms"}` for the "scored in X s on this laptop" line

## Health
- `GET /health` → `{"ok": true, "models": {"aligner": "loaded", "ollama": "up"}}`
  - `models.aligner` is `loaded` or `not_loaded`; `models.ollama` is `up`, `down` or `unknown`. Until a model is wired in, the engine reports `not_loaded` / `unknown`.
