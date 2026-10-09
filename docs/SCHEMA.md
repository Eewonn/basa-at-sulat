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
python -m app.seed                # loads learners and passages (creates the database if missing)
python -m app.seed --reset        # fresh database + seed data in one command (all data is lost)
python -m pytest                  # runs the tests
```

`BASA_DB_PATH` overrides the default location. Without `--reset`, `init_db` refuses to touch an existing database. `seed` is safe to re-run (see [Seed data](#seed-data)).

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

## Seed data

**Task:** P0-BE2-2 · **Code:** [`engine/app/seed.py`](../engine/app/seed.py)

| File | What it holds |
|---|---|
| [`data/learners/learners.json`](../data/learners/learners.json) | 10 synthetic learners, `l_01`–`l_10`, **initials only**, grades 1–3 |
| [`data/passages/passages.json`](../data/passages/passages.json) | Basa passages (see [its README](../data/passages/README.md)) |

### How a run works
1. **Both files are checked before the database is touched.** Every required field must be present, IDs must be unique, text can't be blank, grades must be 1–12, and `language` must be a 2–3 letter lowercase ISO 639 code (`fil`, `eng`, `ilo`, `ceb`, `pam`…). Extra fields, such as a credit line, are ignored. Any problem stops the run with exit code 1 and names the file and entry. Because the check runs first, a typo can't make `--reset` wipe the database.
2. **The database is created if it's missing**, or recreated with `--reset`.
3. **Rows are upserted in one transaction.** New IDs are added and changed rows are updated. Either everything lands or nothing does.
4. **Guard:** if a passage's `text` changed and assessments already use that passage, the run stops and nothing is written. `word_results` are stored by word index (`i`), so new text would quietly misalign every saved result. **To change a passage that's in use,** add the new text under a new ID (e.g. `fil_g2_02`), or use `--reset` if losing results is fine.

**Adding the regional passage:** a teammate who speaks the language adds it to `passages.json` with its ISO code (e.g. `"language": "ilo"`), then runs `python -m app.seed`. No code changes are needed.

### Drawbacks of the upsert approach
We chose "upsert, but guard passages in use" over "insert only" and "always rebuild." These are the trade-offs to know about:

- **Deleting an entry from the JSON doesn't delete it from the database.** The seed only adds and updates. A removed learner or passage stays until `--reset`, and the stale row still shows up in `GET /learners` and `GET /passages`. We don't delete automatically because assessments may reference the row.
- **The JSON overwrites edits made in the database.** If the app later lets teachers rename learners or edit passages, re-seeding silently reverts those changes to whatever the JSON says. Once that feature exists, seeding has to become insert-only or scoped to seed-owned rows.
- **The guard only covers `text`.** Changing `title`, `grade` or `language` on a passage in use goes through. This keeps word indices intact, but past assessments now point to a passage whose metadata changed. For example, a grade change can shift how a past result reads once levels are computed (P1-BE2-2).
- **Learner changes are never guarded.** Changing a learner's `grade` rewrites it for all past checks, because there's no per-assessment snapshot of the grade.
- **The text comparison is exact.** Fixing a typo or even trailing whitespace in a passage in use still counts as a change, and the run is refused. That's deliberate, since even a one-word fix can shift indices, but it means a small correction needs a new passage ID.
- **Fixing a passage in use leaves both versions.** The new-ID workaround keeps the old passage in the database and in the passage picker until it's removed with `--reset` or by hand.

## Rules for code that uses the database

- **Always open connections with `app.db.connect()`.** SQLite turns foreign keys **off** for every new connection by default, and `connect()` turns them on. A plain `sqlite3.connect()` would silently skip cascades and reference checks.
- **`with conn:` does not close the connection.** It only commits or rolls back. Close connections explicitly, for example with `contextlib.closing(connect())`. On Windows, a connection left open keeps the file locked, and `--reset` fails.
- **Change `schema.sql` and this file in the same PR**, and tell the team. There are no migrations yet: after a schema change, run `python -m app.init_db --reset`.
