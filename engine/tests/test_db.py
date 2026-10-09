"""Tests for the SQLite schema and database creation (P0-BE2-1)."""

import sqlite3
from contextlib import closing

import pytest

from app import init_db as init_db_cli
from app.db import DatabaseExistsError, connect, get_db_path, init_db

EXPECTED_TABLES = {
    "learners",
    "passages",
    "assessments",
    "word_results",
    "pauses",
    "books",
    "book_words",
    "practice_attempts",
}


@pytest.fixture
def db_path(tmp_path):
    """A fresh database in a temp folder, so tests never touch the real one."""
    return init_db(tmp_path / "test.db")


@pytest.fixture
def conn(db_path):
    connection = connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def seeded(conn):
    """One learner, passage, draft assessment and book to hang test rows on."""
    conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_01', 'A.B.', 2)")
    conn.execute(
        "INSERT INTO passages (id, title, language, grade, text) "
        "VALUES ('fil_g2_01', 'Ang Palay ni Lina', 'fil', 2, 'Nagtanim si Lina ng palay.')"
    )
    conn.execute(
        "INSERT INTO assessments (id, learner_id, passage_id, duration_sec) "
        "VALUES ('a_01', 'l_01', 'fil_g2_01', 41.2)"
    )
    conn.execute(
        "INSERT INTO books (id, title, language, text) "
        "VALUES ('b_01', 'Ang Palay ni Lina', 'fil', 'Nagtanim si Lina ng palay.')"
    )
    conn.commit()
    return conn


def insert_word(conn, i=0, ai_label="matched", final_label="matched", score=0.9,
                start_sec=0.4, end_sec=1.1, assessment_id="a_01"):
    conn.execute(
        "INSERT INTO word_results (assessment_id, i, text, ai_label, final_label, "
        "score, start_sec, end_sec) VALUES (?, ?, 'Nagtanim', ?, ?, ?, ?, ?)",
        (assessment_id, i, ai_label, final_label, score, start_sec, end_sec),
    )


# --- Creating the database -------------------------------------------------

def test_fresh_database_has_all_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    assert {row["name"] for row in rows} == EXPECTED_TABLES


def test_fresh_database_is_empty(conn):
    for table in EXPECTED_TABLES:
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_creates_missing_parent_folders(tmp_path):
    path = init_db(tmp_path / "nested" / "dir" / "basa.db")
    assert path.exists()


def test_refuses_to_overwrite_existing_database(db_path):
    with closing(connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_01', 'A.B.', 2)")

    with pytest.raises(DatabaseExistsError):
        init_db(db_path)

    # The existing data survived the refused run.
    with closing(connect(db_path)) as conn, conn:
        assert conn.execute("SELECT COUNT(*) FROM learners").fetchone()[0] == 1


def test_reset_replaces_database_with_empty_one(db_path):
    with closing(connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_01', 'A.B.', 2)")

    init_db(db_path, reset=True)

    with closing(connect(db_path)) as conn, conn:
        assert conn.execute("SELECT COUNT(*) FROM learners").fetchone()[0] == 0


def test_env_var_overrides_default_path(tmp_path, monkeypatch):
    target = tmp_path / "from-env.db"
    monkeypatch.setenv("BASA_DB_PATH", str(target))
    assert get_db_path() == target
    assert init_db() == target
    assert target.exists()


def test_broken_schema_leaves_no_file_behind(tmp_path, monkeypatch):
    bad_schema = tmp_path / "bad.sql"
    bad_schema.write_text("CREATE TABLE oops (;", encoding="utf-8")
    monkeypatch.setattr("app.db.SCHEMA_PATH", bad_schema)

    target = tmp_path / "half.db"
    with pytest.raises(sqlite3.Error):
        init_db(target)
    assert not target.exists()


# --- Command-line script ---------------------------------------------------

def test_cli_creates_database(tmp_path, capsys):
    target = tmp_path / "cli.db"
    assert init_db_cli.main(["--path", str(target)]) == 0
    assert target.exists()
    assert "Created database" in capsys.readouterr().out


def test_cli_fails_cleanly_when_database_exists(db_path, capsys):
    assert init_db_cli.main(["--path", str(db_path)]) == 1
    assert "--reset" in capsys.readouterr().err


def test_cli_reset_succeeds(db_path):
    assert init_db_cli.main(["--path", str(db_path), "--reset"]) == 0


# --- Foreign keys ----------------------------------------------------------

def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO assessments (id, learner_id, passage_id, duration_sec) "
            "VALUES ('a_99', 'no_such_learner', 'no_such_passage', 10)"
        )


def test_deleting_assessment_cascades_to_words_and_pauses(seeded):
    insert_word(seeded)
    seeded.execute("INSERT INTO pauses (assessment_id, before_word, seconds) VALUES ('a_01', 3, 1.8)")
    seeded.execute("DELETE FROM assessments WHERE id = 'a_01'")
    assert seeded.execute("SELECT COUNT(*) FROM word_results").fetchone()[0] == 0
    assert seeded.execute("SELECT COUNT(*) FROM pauses").fetchone()[0] == 0


def test_deleting_book_cascades_to_book_words(seeded):
    seeded.execute(
        "INSERT INTO book_words (book_id, i, text, start_sec, end_sec) "
        "VALUES ('b_01', 0, 'Nagtanim', 0.2, 0.9)"
    )
    seeded.execute("DELETE FROM books WHERE id = 'b_01'")
    assert seeded.execute("SELECT COUNT(*) FROM book_words").fetchone()[0] == 0


def test_cannot_delete_assessment_with_practice_history(seeded):
    seeded.execute(
        "INSERT INTO practice_attempts (learner_id, assessment_id, word, result, score) "
        "VALUES ('l_01', 'a_01', 'palay', 'match', 0.8)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("DELETE FROM assessments WHERE id = 'a_01'")


# --- Value checks ----------------------------------------------------------

def test_valid_word_result_is_accepted(seeded):
    insert_word(seeded, ai_label="misread", final_label="matched", score=0.31)
    row = seeded.execute("SELECT ai_label, final_label FROM word_results").fetchone()
    assert (row["ai_label"], row["final_label"]) == ("misread", "matched")


@pytest.mark.parametrize("field", ["ai_label", "final_label"])
def test_unknown_word_label_rejected(seeded, field):
    with pytest.raises(sqlite3.IntegrityError):
        insert_word(seeded, **{field: "hesitated"})


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_word_score_outside_0_to_1_rejected(seeded, score):
    with pytest.raises(sqlite3.IntegrityError):
        insert_word(seeded, score=score)


@pytest.mark.parametrize("score", [0, 1])
def test_word_score_boundaries_accepted(seeded, score):
    insert_word(seeded, score=score)


def test_word_end_before_start_rejected(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        insert_word(seeded, start_sec=2.0, end_sec=1.0)


def test_duplicate_word_index_rejected(seeded):
    insert_word(seeded, i=0)
    with pytest.raises(sqlite3.IntegrityError):
        insert_word(seeded, i=0)


def test_unknown_assessment_status_rejected(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("UPDATE assessments SET status = 'final' WHERE id = 'a_01'")


def test_confirmed_assessment_needs_confirmed_at(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute("UPDATE assessments SET status = 'confirmed' WHERE id = 'a_01'")

    seeded.execute(
        "UPDATE assessments SET status = 'confirmed', "
        "confirmed_at = '2026-10-09T08:00:00.000Z' WHERE id = 'a_01'"
    )


def test_new_assessment_defaults_to_draft(seeded):
    row = seeded.execute("SELECT status, keep_audio FROM assessments WHERE id = 'a_01'").fetchone()
    assert (row["status"], row["keep_audio"]) == ("draft", 0)


def test_non_positive_duration_rejected(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO assessments (id, learner_id, passage_id, duration_sec) "
            "VALUES ('a_02', 'l_01', 'fil_g2_01', 0)"
        )


def test_blank_learner_name_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_02', '   ', 2)")


def test_unknown_practice_result_rejected(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO practice_attempts (learner_id, assessment_id, word, result, score) "
            "VALUES ('l_01', 'a_01', 'palay', 'maybe', 0.5)"
        )


def test_practice_clip_reference_needs_both_parts(seeded):
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO practice_attempts (learner_id, assessment_id, word, book_id, result, score) "
            "VALUES ('l_01', 'a_01', 'palay', 'b_01', 'match', 0.8)"
        )

    seeded.execute(
        "INSERT INTO practice_attempts "
        "(learner_id, assessment_id, word, book_id, word_index, result, score) "
        "VALUES ('l_01', 'a_01', 'palay', 'b_01', 4, 'match', 0.8)"
    )
