# Database schema

**Owner:** Backend 2 · **Task:** P0-BE2-1 · **Source of truth:** [`engine/app/schema.sql`](../engine/app/schema.sql)

SQLite, using only Python's built-in `sqlite3`. The database file lives at `engine/storage/basa.db`, which is git-ignored.

## Quick start

From `engine/`:

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (macOS/Linux: source .venv/bin/activate)
python -m pip install -r requirements.txt

python -m app.init_db             # creates engine/storage/basa.db
python -m app.init_db --reset     # deletes it and starts fresh (all data is lost)
python -m app.init_db --path other.db
python -m pytest                  # runs the tests
```

`BASA_DB_PATH` overrides the default location. Without `--reset`, the script refuses to touch an existing database.

## Tables

| Table | Key | What it holds |
|---|---|---|
| `learners` | `id` | Synthetic names or initials only, plus the grade |
| `passages` | `id` | Basa reading passages (same shape as `data/passages/passages.json`) |
| `assessments` | `id` | One Basa check: learner, passage, duration, `wcpm`, `level`, `status`, audio path |
| `word_results` | `(assessment_id, i)` | Per-word AI label, teacher's final label, score, timings |
| `pauses` | `(assessment_id, before_word)` | Hesitations before a word |
| `books` | `id` | Sulat stories and their model-reading audio path |
| `book_words` | `(book_id, i)` | Word timings in a book's model reading |
| `practice_attempts` | `id` (auto) | Sanay "Say it" results per learner |

Deleting an assessment also deletes its `word_results` and `pauses`. Deleting a book also deletes its `book_words`. Deleting an assessment or book that has `practice_attempts` is **blocked**, because practice history shouldn't vanish silently.

## Things that go beyond the task as written

P0-BE2-1 lists six tables. These choices go further. Please read them if your code touches the database.

### 1. Two extra tables: `pauses` and `book_words`
- **`pauses`:** `POST /assess` returns `pauses[]` ([API.md](API.md)), so it has to be stored somewhere. *Affects: backend-1 (P1-BE1-1), backend-2 (P1-BE2-1).*
- **`book_words`:** `POST /books` and `GET /books/{id}` return per-word timings, and word clips (P2-BE1-2) need them. **Backend-1:** this table is ready for P2-BE1-1. Tell backend-2 if you need a different shape.

### 2. `start_sec` / `end_sec` instead of `start` / `end`
`END` is an SQL keyword. Columns in `word_results` and `book_words` are called `start_sec` and `end_sec`. **The API contract does not change:** code that builds a response maps them back to `start` and `end`.

### 3. Two labels per word: `ai_label` and `final_label`
`ai_label` is what the scorer said and is **never updated**. `final_label` starts as a copy of it and holds the teacher's override (`PATCH /assessments/{id}/words/{i}`), with `overridden_at` set.
- **Why:** WCPM and level are computed from `final_label` (P1-BE2-2), and the kept `ai_label` lets the accuracy report (P3-AI-1) count how often teachers correct the AI.
- **When inserting from `/assess`:** set `final_label = ai_label`.
- The API's `label` field is `final_label`.

### 4. `wcpm` and `level` can be empty, and `level` is free text
Both stay `NULL` until P1-BE2-2 computes them. `level` is not restricted to a fixed list yet, because the names still have to be checked against DepEd's current CRLA profiles. Once they are, we can add a `CHECK`.

### 5. Assessment status rules
- `status` is `draft` (the default) or `confirmed`.
- A `confirmed` assessment **must** have `confirmed_at` set, and a draft must not. The database rejects anything else.
- `keep_audio` is `0` or `1` (default `0`). `audio_path` should be set to `NULL` after the audio is deleted on confirm (P1-BE1-2).

### 6. `practice_attempts` links back to the check
Each attempt stores the `assessment_id` its word came from, so progress (P2-BE2-2) can trace practice to a specific Basa result. `book_id` and `word_index` (the clip reference) must be **both set or both empty**.

### 7. Value checks enforced by the database
Bad data fails at insert time with `sqlite3.IntegrityError` instead of breaking a screen later:
- Labels are only `matched` / `misread` / `skipped`. Practice results are only `match` / `no_match`.
- `score` is between 0 and 1. `end_sec` is not before `start_sec`. Times are not negative.
- `duration_sec` and pause `seconds` are greater than 0. Grades are 1–12.
- Learner names and passage/book text can't be blank.

### 8. Timestamps
`created_at` defaults to UTC ISO-8601 with milliseconds (`2026-10-09T08:00:00.000Z`), so text sorting matches time order. Use the same format when you set `confirmed_at` or `overridden_at` yourself.

### 9. New files outside `engine/app/`
- `engine/requirements.txt` was created with `pytest==9.1.1`. **Add your engine dependencies here**, pinned to exact versions.
- `engine/pytest.ini` lets `python -m pytest` find the `app` package from `engine/`.
- `engine/app/__init__.py` (empty) makes `app` a package.

## Rules for code that uses the database

- **Always open connections with `app.db.connect()`.** SQLite turns foreign keys **off** for every new connection by default, and `connect()` turns them on. A plain `sqlite3.connect()` would silently skip cascades and reference checks.
- **`with conn:` does not close the connection.** It only commits or rolls back. Close connections explicitly, for example with `contextlib.closing(connect())`. On Windows, a connection left open keeps the file locked, and `--reset` fails.
- **Change `schema.sql` and this file in the same PR**, and tell the team. There are no migrations yet: after a schema change, run `python -m app.init_db --reset`.
