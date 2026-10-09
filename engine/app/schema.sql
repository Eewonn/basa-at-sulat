-- Basa at Sulat: SQLite schema (task P0-BE2-1).
-- Column names follow docs/API.md, except start_sec/end_sec (END is a SQL
-- keyword). See docs/SCHEMA.md for every choice that goes beyond the task.

-- Learners. Names are synthetic or initials only: never a real child's name.
CREATE TABLE learners (
    id            TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
    grade         INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 12),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Passages a child reads aloud in a Basa check.
CREATE TABLE passages (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    language    TEXT NOT NULL,
    grade       INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 12),
    text        TEXT NOT NULL CHECK (length(trim(text)) > 0),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    -- Topic for the picture and filter (app.seed.CATEGORIES). Older databases get it from app.db.add_missing_columns.
    category    TEXT
);

-- One Basa check. app.assessments fills wcpm and level on every save and override.
-- level is one of five CRLA names (app/levels.py) but has no CHECK yet: adding one
-- needs a --reset, so it waits for the next schema change (see docs/SCHEMA.md).
CREATE TABLE assessments (
    id            TEXT PRIMARY KEY,
    learner_id    TEXT NOT NULL REFERENCES learners (id),
    passage_id    TEXT NOT NULL REFERENCES passages (id),
    duration_sec  REAL NOT NULL CHECK (duration_sec > 0),
    wcpm          REAL CHECK (wcpm IS NULL OR wcpm >= 0),
    level         TEXT,
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'confirmed')),
    -- NULL once the audio is deleted on confirm (P1-BE1-2).
    audio_path    TEXT,
    keep_audio    INTEGER NOT NULL DEFAULT 0 CHECK (keep_audio IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    confirmed_at  TEXT,
    -- A confirmed check must say when it was confirmed, and a draft must not.
    CHECK ((status = 'confirmed') = (confirmed_at IS NOT NULL))
);

-- "Latest check for this learner" (practice sets, progress).
CREATE INDEX idx_assessments_learner_created
    ON assessments (learner_id, created_at);

-- Per-word result of a check. ai_label is what the scorer said and is never
-- changed; final_label starts equal to it and holds the teacher's override.
-- Keeping both lets us measure how often teachers correct the AI.
CREATE TABLE word_results (
    assessment_id  TEXT NOT NULL REFERENCES assessments (id) ON DELETE CASCADE,
    i              INTEGER NOT NULL CHECK (i >= 0),
    text           TEXT NOT NULL,
    ai_label       TEXT NOT NULL CHECK (ai_label IN ('matched', 'misread', 'skipped')),
    final_label    TEXT NOT NULL CHECK (final_label IN ('matched', 'misread', 'skipped')),
    score          REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
    start_sec      REAL CHECK (start_sec IS NULL OR start_sec >= 0),
    end_sec        REAL CHECK (end_sec IS NULL OR end_sec >= start_sec),
    overridden_at  TEXT,
    PRIMARY KEY (assessment_id, i)
);

-- Hesitations, reported separately from word labels (see docs/API.md).
CREATE TABLE pauses (
    assessment_id  TEXT NOT NULL REFERENCES assessments (id) ON DELETE CASCADE,
    before_word    INTEGER NOT NULL CHECK (before_word >= 0),
    seconds        REAL NOT NULL CHECK (seconds > 0),
    PRIMARY KEY (assessment_id, before_word)
);

-- Sulat books: a story plus a fluent speaker's model reading.
CREATE TABLE books (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    language    TEXT NOT NULL,
    text        TEXT NOT NULL CHECK (length(trim(text)) > 0),
    audio_path  TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Word timings in a book's model reading, used for highlighting and clips.
CREATE TABLE book_words (
    book_id    TEXT NOT NULL REFERENCES books (id) ON DELETE CASCADE,
    i          INTEGER NOT NULL CHECK (i >= 0),
    text       TEXT NOT NULL,
    start_sec  REAL NOT NULL CHECK (start_sec >= 0),
    end_sec    REAL NOT NULL CHECK (end_sec >= start_sec),
    PRIMARY KEY (book_id, i)
);

-- Sanay "Say it" attempts. assessment_id is the check the word came from, so
-- progress can be traced back to a specific Basa result. Attempts are history:
-- deleting an assessment or book that still has attempts is blocked.
CREATE TABLE practice_attempts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id     TEXT NOT NULL REFERENCES learners (id),
    assessment_id  TEXT NOT NULL REFERENCES assessments (id),
    word           TEXT NOT NULL,
    book_id        TEXT REFERENCES books (id),
    word_index     INTEGER CHECK (word_index IS NULL OR word_index >= 0),
    result         TEXT NOT NULL CHECK (result IN ('match', 'no_match')),
    score          REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    -- A clip reference needs both parts or neither.
    CHECK ((book_id IS NULL) = (word_index IS NULL))
);

CREATE INDEX idx_practice_attempts_learner
    ON practice_attempts (learner_id, created_at);
