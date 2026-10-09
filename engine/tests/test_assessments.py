"""Tests for storing checks and teacher overrides (P1-BE2-1)."""

import copy
import json
from contextlib import closing
from pathlib import Path

import pytest

from app.assessments import (
    AssessmentConfirmedError,
    AssessmentNotFoundError,
    InvalidAssessmentError,
    confirm_assessment,
    get_assessment,
    override_word,
    save_assessment,
)
from app.db import connect
from app.seed import seed_db

# The frontend's mock result. It uses the real seed ids l_07 and fil_g2_01,
# and its 7 words are the passage's first 7.
FIXTURE = Path(__file__).resolve().parents[2] / "docs" / "api" / "assess.example.json"
EXAMPLE = json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def conn(tmp_path):
    """A temp database with the real seed learners and passages."""
    db_path = tmp_path / "test.db"
    seed_db(db_path)
    connection = connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def result():
    """A fresh copy of the example, so tests can edit it freely."""
    return copy.deepcopy(EXAMPLE)


@pytest.fixture
def saved(conn, result):
    """The example stored as a draft."""
    return save_assessment(conn, result)


def word_row(conn, i, assessment_id="a_123"):
    return conn.execute(
        "SELECT ai_label, final_label, overridden_at FROM word_results "
        "WHERE assessment_id = ? AND i = ?",
        (assessment_id, i),
    ).fetchone()


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# --- Saving: happy paths ---------------------------------------------------

def test_save_returns_the_contract_shape(saved):
    expected = copy.deepcopy(EXAMPLE)
    # Recomputed from the labels: 5 matched words in 41.2 s, and 5 of the
    # passage's 23 words (22%) is High Emerging.
    expected["wcpm"] = 7
    expected["level"] = "High Emerging"
    assert saved == expected


def test_save_stores_ai_label_as_the_starting_final_label(conn, saved):
    row = word_row(conn, 4)
    assert (row["ai_label"], row["final_label"], row["overridden_at"]) == (
        "misread", "misread", None
    )


def test_save_ignores_the_callers_wcpm_and_level(conn, result):
    result["wcpm"] = 999
    result["level"] = "Grade Level Ready"
    saved = save_assessment(conn, result)
    assert (saved["wcpm"], saved["level"]) == (7, "High Emerging")


def test_save_stores_audio_path_and_starts_as_draft(conn, result):
    save_assessment(conn, result, audio_path="storage/a_123.wav")
    row = conn.execute(
        "SELECT audio_path, status, keep_audio FROM assessments WHERE id = 'a_123'"
    ).fetchone()
    assert tuple(row) == ("storage/a_123.wav", "draft", 0)


def test_save_without_pauses_key(conn, result):
    del result["pauses"]
    assert save_assessment(conn, result)["pauses"] == []


def test_save_returns_words_in_index_order(conn, result):
    result["words"].reverse()
    saved = save_assessment(conn, result)
    assert [word["i"] for word in saved["words"]] == list(range(7))


def test_save_allows_null_timings(conn, result):
    # A skipped word may have no timing from the scorer.
    result["words"][3]["start"] = None
    result["words"][3]["end"] = None
    saved = save_assessment(conn, result)
    assert (saved["words"][3]["start"], saved["words"][3]["end"]) == (None, None)


# --- Saving: bad input -----------------------------------------------------

@pytest.mark.parametrize("field", ["assessment_id", "learner_id", "passage_id",
                                   "duration_sec", "words"])
def test_save_rejects_missing_field(conn, result, field):
    del result[field]
    with pytest.raises(InvalidAssessmentError, match=field):
        save_assessment(conn, result)


def test_save_rejects_non_object(conn):
    with pytest.raises(InvalidAssessmentError, match="object"):
        save_assessment(conn, ["not", "a", "dict"])


def test_save_rejects_unknown_learner(conn, result):
    result["learner_id"] = "l_99"
    with pytest.raises(InvalidAssessmentError, match="unknown learner 'l_99'"):
        save_assessment(conn, result)


def test_save_rejects_unknown_passage(conn, result):
    result["passage_id"] = "fil_g9_99"
    with pytest.raises(InvalidAssessmentError, match="unknown passage 'fil_g9_99'"):
        save_assessment(conn, result)


@pytest.mark.parametrize("duration", [0, -1, "41.2", True, None])
def test_save_rejects_bad_duration(conn, result, duration):
    result["duration_sec"] = duration
    with pytest.raises(InvalidAssessmentError, match="duration_sec"):
        save_assessment(conn, result)


@pytest.mark.parametrize("words", [[], None, "Nagtanim"])
def test_save_rejects_empty_or_non_list_words(conn, result, words):
    result["words"] = words
    with pytest.raises(InvalidAssessmentError, match="non-empty list"):
        save_assessment(conn, result)


def test_save_rejects_word_that_is_not_an_object(conn, result):
    result["words"][0] = "Nagtanim"
    with pytest.raises(InvalidAssessmentError, match=r"words\[0\] is not an object"):
        save_assessment(conn, result)


def test_save_rejects_word_missing_a_field(conn, result):
    del result["words"][2]["score"]
    with pytest.raises(InvalidAssessmentError, match=r"words\[2\]: missing score"):
        save_assessment(conn, result)


@pytest.mark.parametrize("i", [-1, 1.0, "1", True])
def test_save_rejects_bad_word_index(conn, result, i):
    result["words"][1]["i"] = i
    with pytest.raises(InvalidAssessmentError, match="whole number"):
        save_assessment(conn, result)


def test_save_rejects_duplicate_word_index(conn, result):
    result["words"][1]["i"] = 0
    result["words"][1]["text"] = "Nagtanim"
    with pytest.raises(InvalidAssessmentError, match="index 0 appears twice"):
        save_assessment(conn, result)


def test_save_rejects_index_past_the_passage(conn, result):
    result["words"][6]["i"] = 500
    with pytest.raises(InvalidAssessmentError, match="past the passage's last word"):
        save_assessment(conn, result)


def test_save_rejects_text_that_doesnt_match_the_passage(conn, result):
    # A shifted index is the misalignment this check exists to catch.
    result["words"][4]["text"] = "pala"
    with pytest.raises(InvalidAssessmentError, match="'pala' doesn't match .* 'palay'"):
        save_assessment(conn, result)


def test_save_rejects_unknown_label(conn, result):
    result["words"][0]["label"] = "hesitated"
    with pytest.raises(InvalidAssessmentError, match="'label' must be one of"):
        save_assessment(conn, result)


def test_save_rejects_pauses_that_are_not_a_list(conn, result):
    result["pauses"] = {"before_word": 3, "seconds": 1.8}
    with pytest.raises(InvalidAssessmentError, match="'pauses' must be a list"):
        save_assessment(conn, result)


@pytest.mark.parametrize("pause", [{"seconds": 1.8}, {"before_word": 500, "seconds": 1.8},
                                   {"before_word": -1, "seconds": 1.8}, "3"])
def test_save_rejects_bad_pause(conn, result, pause):
    result["pauses"] = [pause]
    with pytest.raises(InvalidAssessmentError, match=r"pauses\[0\]"):
        save_assessment(conn, result)


def test_save_rejects_duplicate_assessment_id(conn, result):
    save_assessment(conn, result)
    with pytest.raises(InvalidAssessmentError, match="could not be saved"):
        save_assessment(conn, copy.deepcopy(EXAMPLE))


@pytest.mark.parametrize("field, value", [("score", 1.5), ("end", 0.1)])
def test_schema_violation_saves_nothing(conn, result, field, value):
    # The bad value is on the last word, so earlier rows were already inserted
    # when the database rejects it. All of them must be rolled back.
    result["words"][-1][field] = value
    with pytest.raises(InvalidAssessmentError, match="could not be saved"):
        save_assessment(conn, result)
    assert count(conn, "assessments") == 0
    assert count(conn, "word_results") == 0
    assert count(conn, "pauses") == 0


def test_bad_pause_seconds_saves_nothing(conn, result):
    result["pauses"] = [{"before_word": 3, "seconds": 0}]
    with pytest.raises(InvalidAssessmentError):
        save_assessment(conn, result)
    assert count(conn, "assessments") == 0


# --- Reading ---------------------------------------------------------------

def test_get_unknown_assessment(conn):
    with pytest.raises(AssessmentNotFoundError, match="no assessment 'a_404'"):
        get_assessment(conn, "a_404")


# --- Overrides -------------------------------------------------------------

def test_override_changes_label_and_recomputes(conn, saved):
    updated = override_word(conn, "a_123", 3, "matched")
    assert updated["words"][3]["label"] == "matched"
    # 6 matched words in 41.2 s is 8.74 per minute.
    assert (updated["wcpm"], updated["level"]) == (9, "High Emerging")
    assert get_assessment(conn, "a_123") == updated


def test_override_can_move_the_level_up(conn, result):
    # A full reading of the 23-word passage with 18 matched (78%) is Developing.
    # One override makes it 19 (83%), which is Transitioning.
    passage = conn.execute("SELECT text FROM passages WHERE id = 'fil_g2_01'").fetchone()
    passage_words = passage["text"].split()
    result["words"] = [
        {"i": i, "text": text, "label": "matched" if i < 18 else "misread",
         "score": 0.9, "start": None, "end": None}
        for i, text in enumerate(passage_words)
    ]
    result["pauses"] = []
    result["duration_sec"] = 20.0
    assert save_assessment(conn, result)["level"] == "Developing"

    updated = override_word(conn, "a_123", 18, "matched")
    assert updated["level"] == "Transitioning"
    assert get_assessment(conn, "a_123")["level"] == "Transitioning"


def test_override_keeps_the_ai_label_and_records_when(conn, saved):
    override_word(conn, "a_123", 3, "matched")
    row = word_row(conn, 3)
    assert (row["ai_label"], row["final_label"]) == ("skipped", "matched")
    assert row["overridden_at"].endswith("Z")


def test_override_can_lower_the_score(conn, saved):
    updated = override_word(conn, "a_123", 0, "misread")
    # 4 matched words in 41.2 s is 5.83 per minute.
    assert updated["wcpm"] == 6


def test_reverting_to_the_ai_label_clears_overridden_at(conn, saved):
    override_word(conn, "a_123", 4, "matched")
    updated = override_word(conn, "a_123", 4, "misread")
    assert word_row(conn, 4)["overridden_at"] is None
    assert updated["wcpm"] == 7


def test_override_only_touches_its_own_assessment(conn, saved):
    other = copy.deepcopy(EXAMPLE)
    other["assessment_id"] = "a_124"
    save_assessment(conn, other)
    override_word(conn, "a_123", 3, "matched")
    assert word_row(conn, 3, "a_124")["final_label"] == "skipped"
    assert get_assessment(conn, "a_124")["wcpm"] == 7


def test_override_rejects_unknown_label(conn, saved):
    with pytest.raises(InvalidAssessmentError, match="'label' must be one of"):
        override_word(conn, "a_123", 3, "correct")


def test_override_unknown_assessment(conn, saved):
    with pytest.raises(AssessmentNotFoundError, match="no assessment 'a_404'"):
        override_word(conn, "a_404", 3, "matched")


def test_override_unknown_word(conn, saved):
    with pytest.raises(AssessmentNotFoundError, match="has no word 7"):
        override_word(conn, "a_123", 7, "matched")


def test_override_after_confirm_is_refused_and_changes_nothing(conn, saved):
    confirm_assessment(conn, "a_123")
    with pytest.raises(AssessmentConfirmedError, match="confirmed"):
        override_word(conn, "a_123", 3, "matched")
    assert word_row(conn, 3)["final_label"] == "skipped"


# --- Confirm ---------------------------------------------------------------

def test_confirm_marks_final_and_records_time(conn, saved):
    confirmed = confirm_assessment(conn, "a_123")
    assert confirmed["status"] == "confirmed"
    row = conn.execute(
        "SELECT confirmed_at, keep_audio FROM assessments WHERE id = 'a_123'"
    ).fetchone()
    assert row["confirmed_at"].endswith("Z")
    assert row["keep_audio"] == 0


def test_confirm_records_keep_audio(conn, saved):
    confirm_assessment(conn, "a_123", keep_audio=True)
    keep = conn.execute("SELECT keep_audio FROM assessments WHERE id = 'a_123'").fetchone()[0]
    assert keep == 1


def test_confirm_leaves_audio_path_for_backend_1(conn, result):
    # Deleting the file and clearing audio_path is P1-BE1-2's job.
    save_assessment(conn, result, audio_path="storage/a_123.wav")
    confirm_assessment(conn, "a_123")
    path = conn.execute("SELECT audio_path FROM assessments WHERE id = 'a_123'").fetchone()[0]
    assert path == "storage/a_123.wav"


def test_confirm_twice_is_refused(conn, saved):
    confirm_assessment(conn, "a_123")
    with pytest.raises(AssessmentConfirmedError):
        confirm_assessment(conn, "a_123", keep_audio=True)


def test_confirm_unknown_assessment(conn):
    with pytest.raises(AssessmentNotFoundError):
        confirm_assessment(conn, "a_404")


def test_changes_are_visible_to_a_new_connection(tmp_path):
    # Guards against a missing commit: the API opens a new connection per request.
    db_path = tmp_path / "test.db"
    seed_db(db_path)
    with closing(connect(db_path)) as first:
        save_assessment(first, copy.deepcopy(EXAMPLE))
        override_word(first, "a_123", 3, "matched")
    with closing(connect(db_path)) as second:
        assert get_assessment(second, "a_123")["words"][3]["label"] == "matched"
