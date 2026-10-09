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

`wcpm` (words correct per minute) is a whole number: `matched` words ÷ the recording's minutes, computed by the engine from the final labels, so it follows teacher overrides. `level` is one of `Low Emerging`, `High Emerging`, `Developing`, `Transitioning`, `At Grade Level` (lowest first), computed from accuracy and `wcpm` and also following overrides. **It is an estimate from reading fluency, not an official CRLA profile**, because the app asks no comprehension questions. Label it that way in the UI (for example "Estimated level"). See `docs/DECISIONS.md` for the rules. A saved check always has both; the database allows `NULL`, so clients should still not crash on one.

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

`timings` is the processing time on this laptop, for the "scored in X s" line. `align_ms` and `score_ms` come from `ai.score`; if a scorer reports no split, `align_ms` is the whole call and `score_ms` is `0`. The result is stored as a draft, so the teacher can override words with `PATCH` right away. `wcpm` and `level` are computed by the engine when the result is saved.

Errors: `400` if the audio can't be read, `404` for an unknown `passage_id` or `learner_id`, `422` if a field is missing, `503` if the engine has no database yet (run `python -m app.seed` in `engine/`) or the scoring model isn't installed, `500` if scoring fails or the result can't be saved. Scoring can take a while (about 0.6× the recording length on CPU, plus ~10 s for the first call unless the engine was started with `BASA_WARM_UP=1`), so the app should wait and show a progress state.

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
Marks the assessment final (`status: "confirmed"`) and deletes the child's audio unless the body is `{"keep_audio": true}`. An empty body means `keep_audio: false`. Returns the confirmed assessment.

| Status | When |
|---|---|
| `404` | No assessment with that id |
| `409` | Already confirmed. A client can treat this as "already saved", and a second call never deletes a kept recording |
| `422` | `keep_audio` isn't `true` or `false` |
| `500` | Confirmed, but the audio file could not be deleted (for example a locked file). The row stays confirmed with its audio path set, so the deletion is still owed. The engine retries it at its next start |

A file that is already gone counts as deleted.

## Learners and passages
- `GET /learners` → `[{"id", "display_name", "grade"}]` (display names are synthetic or initials only)
- `GET /passages` → `[{"id", "title", "language", "grade", "text"}]`

## Sulat: books
- `POST /books`: multipart form with `title`, `language` (2-3 lowercase letters, such as `fil`, `eng`, `ilo`), `text` and `audio` (the model reading). Returns `{"id", "words": [{"i", "text", "start", "end"}]}`. Use a fluent speaker's complete reading of the story, and keep digits and dashes out of it, because words with no letters get zero-length times.
- `GET /books/{id}` → `{"id", "title", "language", "text", "words": [{"i", "text", "start", "end"}]}`
- `GET /books/{id}/audio` → the full model reading (`audio/wav`, 16 kHz mono)
- `GET /books/{id}/clips/{i}` → audio for word `i` only (`audio/wav`, 16 kHz mono), cut from the model reading between that word's `start` and `end`

`POST /books` errors (body `{"detail": "<what went wrong>"}`). A rejected upload keeps nothing: no audio file and no book.

| Status | When |
|---|---|
| `400` | The audio can't be read |
| `413` | The audio is over 25 MB |
| `422` | A field is missing or blank, `language` isn't a 2-3 letter lowercase code, the story is over 3,000 words, or the audio is too short to hold the story |
| `500` | Timing or saving failed |
| `503` | The engine has no database yet, or the scoring model isn't installed |

`GET /books/{id}` and `GET /books/{id}/audio` return `404` for an unknown id.

`GET /books/{id}/clips/{i}` errors: `404` for an unknown book, an unknown word index, or missing audio; `422` if `i` isn't a whole number, or the word has no audio in the reading (words with no letters, such as digits, get zero-length times, so the app should not offer "Hear it" for them); `503` if the engine has no database yet. A word that runs past the end of the recording is cut at the end.

## Sanay: practice
- `GET /learners/{id}/practice` → `{"items": [{"word", "sentence", "book_id", "word_index"}]}`, built from the child's latest confirmed check
  - Words are the ones the teacher left as `misread` or `skipped` (final labels), in passage order, once each, with surrounding punctuation removed. `sentence` is the passage sentence the word was missed in.
  - `book_id` / `word_index` point at the first timed occurrence of the word in a Sulat book of the same language, for `GET /books/{id}/clips/{i}`. Both are `null` when no book has the word.
  - `{"items": []}` when the learner has no confirmed check (drafts are not practised). `404` for an unknown learner.
- `POST /practice/check`: multipart form with `audio` and `word`. Returns `{"word", "result": "match" | "no_match", "score"}`
- `GET /learners/{id}/progress` → `{"checks": [{"assessment_id", "passage_id", "confirmed_at", "wcpm", "level"}, ...], "words": [{"i", "text", "before", "after"}], "wcpm_before", "wcpm_after", "wcpm_change"}`
  - Compares the learner's latest two **confirmed** checks **on the same passage**: the newest check that has an earlier one on its passage, and the newest of those earlier ones. `checks` is `[before, after]`. If the newest check is on a passage read only once, an older pair is used, so `after` is not always the learner's latest check.
  - `words` lists every passage word in passage order, one per position (repeats are not merged), with `text` as written (punctuation kept). `before`/`after` are the teacher's final labels (`matched`, `misread`, `skipped`), or `null` if that check has no result for the word.
  - `wcpm_change` is `wcpm_after - wcpm_before` and can be negative.
  - With no same-passage pair (fewer than two confirmed checks, or checks on different passages): `200` with `{"checks": [], "words": [], "wcpm_before": null, "wcpm_after": null, "wcpm_change": null}`. Drafts are ignored. `404` for an unknown learner.

## Class view
- `GET /class` → `{"groups": [{"level", "learner_ids", "common_missed_words", "draft_plan"}]}`
- `GET /class/export.csv`

## Proposed by frontend (needs team agreement)
These support the learner profile and story categories. Until the engine implements them, the app uses sample data for them.
- `category` on every passage: `"bukid" | "pamilya" | "hayop" | "kalikasan" | "paaralan"`
- `GET /learners` items also include `stars`, `streak_days` and `latest_wcpm` (for the class summary cards)
- `GET /learners/{id}/stats` → `{"stars", "streak_days", "minutes_read", "wcpm_history": [{"date", "wcpm"}], "practicing": ["palay", ...], "days_read": ["2026-10-10", ...]}` (`days_read` = dates with a check or practice, for the reading card)
  - stars = words gotten right in Sanay; streak = consecutive days with a check or practice; minutes = recording time
- `POST /practice/check` also takes `learner_id`, so a correct word can earn a star
- `GET /assessments/recent` → `[{"assessment_id", "learner_id", "display_name", "date", "passage_title", "wcpm"}]` (Basa tab)
- `GET /books` → `[{"id", "title", "language", "category", "text", "reader", "has_recording", "duration_sec"}]`; `GET /books/{id}` adds `words` timings; `POST /books` also takes `category` and `reader`, and its story becomes a passage
- `GET /storage` → `{"audio_files", "audio_mb", "db_mb", "data_dir"}`; `DELETE /audio` deletes all children's recordings (book readings are kept) → `{"deleted"}`
- `POST /learners` `{"display_name"}` and `PATCH /learners/{id}` `{"display_name"}` (Settings → Klase)
- `GET /class/settings` → `{"teacher_name", "section", "grade"}` and `PATCH /class/settings` (greeting, Klase subtitle)

## Health
- `GET /health` → `{"ok": true, "models": {"aligner": "loaded", "ollama": "up"}}`
  - `models.aligner` is `loaded` or `not_loaded`; `models.ollama` is `up`, `down` or `unknown`. The engine reports `not_loaded` until the aligner is in memory (after the first `/assess`, or at startup with `BASA_WARM_UP=1`), and `unknown` for Ollama until it is wired in.

## Contract changes

### 2026-10-10 · backend-2 (P2-BE2-2)
- `GET /learners/{id}/progress` is live. **Additions to the old one-line contract:** `i` on each word (its passage index), the `checks` item fields, and `wcpm_change`.
- Only checks on the **same passage** are compared, because a word-by-word comparison needs the same text. **Frontend:** `after` may not be the learner's latest check (see above), so label the pair with its `confirmed_at` dates.
- `before`/`after` can be `null` for a word a check has no result for. To show only what changed, filter on `before != after`.
- Practice attempts are not included yet.

### 2026-10-10 · backend-2 (P2-BE2-1)
- `GET /learners/{id}/practice` is live. `book_id` and `word_index` can be `null` (no book has the word yet). **Frontend:** `PracticeItem` in `desktop/src/renderer/src/api/types.ts` needs `book_id: string | null` and `word_index: number | null`, and "Hear it" should be hidden or disabled when they are `null`.
- **The set is not capped.** A struggling reader can get a long one: in the demo seed, `l_01` gets 18 words and `l_05` gets 16. **Frontend decides** how many to show per session (a cap, paging, or "more later"). Items are in passage order, so taking the first N keeps them in reading order.
- Clips are matched by word text, because passages and books aren't linked. A word gets a clip only once a book in the same language contains it.

### 2026-10-10 · backend-2 (P1-BE2-2)
- `level` is now computed for every saved check. It is one of `Low Emerging`, `High Emerging`, `Developing`, `Transitioning`, `At Grade Level`. It is a **fluency-based estimate** using CRLA's names, not an official CRLA result (see `docs/DECISIONS.md`).
- An override can change `level` as well as `wcpm`.
- **Frontend:** show it as an estimate, and map the five names to colors.

### 2026-10-10 · backend-2 (P1-BE2-1)
- `PATCH /assessments/{id}/words/{i}` now lists its error responses (404, 409, 422, 503).
- `level` is `null` until P1-BE2-2. **Frontend:** `desktop/src/renderer/src/api/types.ts` types it as `string`; it should be `string | null`.
- `wcpm` is defined (whole number, `matched` words per minute, from the final labels).
- `start`/`end` can be `null` for a word with no timing (the database already allowed this). **Frontend:** `Word.start`/`Word.end` should be `number | null`.
