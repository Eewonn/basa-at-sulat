"""Tests for progress tracking (P2-BE2-2): app/progress.py and GET /learners/{id}/progress."""

from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.assessments import confirm_assessment, override_word, save_assessment
from app.db import connect
from app.demo_seed import load_demo_checks, prepare_demo_checks
from app.main import app
from app.practice import LearnerNotFoundError
from app.progress import build_progress, empty_progress, find_check_pair
from app.seed import DEFAULT_DEMO_CHECKS_DIR, DEFAULT_DEMO_CONFIG_PATH, seed_db

# Same helpers as the practice tests: a check on fil_g2_01 for l_07, all words matched unless given.
from tests.test_practice import FIL_TEXT, make_result, save_check, set_times

client = TestClient(app)


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    seed_db(path)
    with closing(connect(path)) as conn:
        yield conn


def passage_text(conn, passage_id):
    return conn.execute("SELECT text FROM passages WHERE id = ?", (passage_id,)).fetchone()["text"]


def save_other_passage_check(conn, assessment_id, passage_id="fil_g2_02", **kwargs):
    save_check(conn, assessment_id, passage_id=passage_id,
               text=passage_text(conn, passage_id), **kwargs)


def pair_ids(conn, learner_id="l_07"):
    pair = find_check_pair(conn, learner_id)
    return None if pair is None else (pair[0]["id"], pair[1]["id"])


def changed(progress):
    return {w["i"]: (w["before"], w["after"]) for w in progress["words"] if w["before"] != w["after"]}


# --- The comparison -----------------------------------------------------------

def test_two_checks_are_compared_word_by_word(conn):
    save_check(conn, "a_1", {4: "misread", 11: "skipped"})
    set_times(conn, "a_1", "2026-09-07T00:00:00.000Z")
    save_check(conn, "a_2", {11: "misread", 18: "skipped"})
    set_times(conn, "a_2", "2026-10-05T00:00:00.000Z")

    progress = build_progress(conn, "l_07")

    assert [c["assessment_id"] for c in progress["checks"]] == ["a_1", "a_2"]
    assert progress["checks"][0] == {
        "assessment_id": "a_1", "passage_id": "fil_g2_01",
        "confirmed_at": "2026-09-07T00:00:00.000Z",
        "wcpm": progress["wcpm_before"], "level": progress["checks"][0]["level"],
    }
    assert progress["words"][4] == {"i": 4, "text": "palay", "before": "misread", "after": "matched"}
    assert changed(progress) == {
        4: ("misread", "matched"),
        11: ("skipped", "misread"),
        18: ("matched", "skipped"),
    }


def test_every_passage_word_is_listed_in_order_with_punctuation_kept(conn):
    save_check(conn, "a_1")
    save_check(conn, "a_2")
    words = build_progress(conn, "l_07")["words"]
    assert [w["text"] for w in words] == FIL_TEXT.split()
    assert [w["i"] for w in words] == list(range(len(FIL_TEXT.split())))
    assert words[6]["text"] == "bukid."  # repeats and punctuation are not merged or stripped


def test_wcpm_change_is_after_minus_before(conn):
    # 30-second checks: 21 matched words is 42 WCPM, 23 is 46.
    save_check(conn, "a_1", {4: "misread", 11: "skipped"})
    save_check(conn, "a_2")
    progress = build_progress(conn, "l_07")
    assert (progress["wcpm_before"], progress["wcpm_after"], progress["wcpm_change"]) == (42, 46, 4)


def test_a_slower_second_check_gives_a_negative_change(conn):
    save_check(conn, "a_1")
    save_check(conn, "a_2", {0: "skipped", 1: "skipped"})
    assert build_progress(conn, "l_07")["wcpm_change"] == -4


def test_a_missing_wcpm_gives_no_change_instead_of_failing(conn):
    # Saving always fills wcpm, but the column allows NULL (docs/SCHEMA.md), so set it by hand.
    save_check(conn, "a_1")
    save_check(conn, "a_2")
    with conn:
        conn.execute("UPDATE assessments SET wcpm = NULL WHERE id = 'a_1'")

    progress = build_progress(conn, "l_07")
    assert progress["wcpm_before"] is None
    assert progress["wcpm_after"] == 46
    assert progress["wcpm_change"] is None
    assert progress["words"]  # the word comparison still comes back


def test_teacher_overrides_count(conn):
    save_check(conn, "a_1", {4: "misread"})
    save_check(conn, "a_2", {4: "misread"}, confirm=False)
    override_word(conn, "a_2", 4, "matched")
    confirm_assessment(conn, "a_2")

    progress = build_progress(conn, "l_07")
    assert changed(progress) == {4: ("misread", "matched")}
    assert progress["wcpm_change"] == 2


def test_a_word_missing_from_a_check_is_null_on_that_side(conn):
    # The scorer may leave words out; the passage still decides which words are listed.
    result = make_result("a_1")
    result["words"] = [w for w in result["words"] if w["i"] != 22]
    save_assessment(conn, result)
    confirm_assessment(conn, "a_1")
    save_check(conn, "a_2")

    words = build_progress(conn, "l_07")["words"]
    assert len(words) == len(FIL_TEXT.split())
    assert words[22] == {"i": 22, "text": "puno.", "before": None, "after": "matched"}


# --- Which two checks ---------------------------------------------------------

def test_the_latest_two_on_the_same_passage_are_used(conn):
    for n, day in enumerate(("2026-09-01", "2026-09-15", "2026-10-01"), start=1):
        save_check(conn, f"a_{n}")
        set_times(conn, f"a_{n}", f"{day}T00:00:00.000Z")
    assert pair_ids(conn) == ("a_2", "a_3")


def test_order_is_by_confirmation_time_not_by_id(conn):
    save_check(conn, "a_9")
    set_times(conn, "a_9", "2026-09-01T00:00:00.000Z")
    save_check(conn, "a_1")
    set_times(conn, "a_1", "2026-10-01T00:00:00.000Z")
    assert pair_ids(conn) == ("a_9", "a_1")


def test_same_confirmation_time_falls_back_to_creation_time(conn):
    save_check(conn, "a_9")
    set_times(conn, "a_9", "2026-10-01T00:00:00.000Z", created_at="2026-09-01T00:00:00.000Z")
    save_check(conn, "a_1")
    set_times(conn, "a_1", "2026-10-01T00:00:00.000Z", created_at="2026-09-02T00:00:00.000Z")
    assert pair_ids(conn) == ("a_9", "a_1")


def test_checks_on_different_passages_are_not_paired(conn):
    save_check(conn, "a_1")
    save_other_passage_check(conn, "a_2")
    assert pair_ids(conn) is None
    assert build_progress(conn, "l_07") == empty_progress()


def test_a_newest_check_on_a_new_passage_falls_back_to_the_older_pair(conn):
    save_check(conn, "a_1")
    set_times(conn, "a_1", "2026-09-01T00:00:00.000Z")
    save_check(conn, "a_2")
    set_times(conn, "a_2", "2026-09-15T00:00:00.000Z")
    save_other_passage_check(conn, "a_3")
    set_times(conn, "a_3", "2026-10-01T00:00:00.000Z")
    assert pair_ids(conn) == ("a_1", "a_2")


def test_the_newest_pair_wins_across_passages(conn):
    # fil_g2_01 was read on 09-01 and 09-10; fil_g2_02 on 09-05 and 10-01. The fil_g2_02 pair is newer.
    save_check(conn, "a_1")
    set_times(conn, "a_1", "2026-09-01T00:00:00.000Z")
    save_other_passage_check(conn, "b_1")
    set_times(conn, "b_1", "2026-09-05T00:00:00.000Z")
    save_check(conn, "a_2")
    set_times(conn, "a_2", "2026-09-10T00:00:00.000Z")
    save_other_passage_check(conn, "b_2")
    set_times(conn, "b_2", "2026-10-01T00:00:00.000Z")

    progress = build_progress(conn, "l_07")
    assert [c["assessment_id"] for c in progress["checks"]] == ["b_1", "b_2"]
    assert [w["text"] for w in progress["words"]] == passage_text(conn, "fil_g2_02").split()


def test_drafts_are_ignored(conn):
    save_check(conn, "a_1")
    save_check(conn, "a_2", confirm=False)
    assert pair_ids(conn) is None


def test_a_newer_draft_does_not_replace_a_confirmed_check(conn):
    save_check(conn, "a_1")
    save_check(conn, "a_2")
    save_check(conn, "a_3", confirm=False)
    assert pair_ids(conn) == ("a_1", "a_2")


def test_other_learners_checks_are_not_mixed_in(conn):
    save_check(conn, "a_1")
    save_check(conn, "a_2", learner_id="l_08")
    assert pair_ids(conn) is None
    assert pair_ids(conn, "l_08") is None


# --- Nothing to compare ---------------------------------------------------------

def test_no_checks_gives_the_empty_shape(conn):
    assert build_progress(conn, "l_07") == empty_progress()


def test_one_check_gives_the_empty_shape(conn):
    save_check(conn, "a_1")
    assert build_progress(conn, "l_07") == empty_progress()


def test_the_empty_shape_is_a_fresh_copy(conn):
    first = build_progress(conn, "l_07")
    first["checks"].append("changed")
    assert build_progress(conn, "l_07")["checks"] == []


def test_unknown_learner_raises(conn):
    with pytest.raises(LearnerNotFoundError):
        build_progress(conn, "l_404")


# --- Demo seed ------------------------------------------------------------------

def test_demo_before_and_after_pairs_are_compared(conn):
    """The demo seed promises l_03, l_07, l_09 and l_10 a before-and-after pair (docs/SCHEMA.md)."""
    load_demo_checks(conn, prepare_demo_checks(DEFAULT_DEMO_CONFIG_PATH, DEFAULT_DEMO_CHECKS_DIR))
    for learner_id in ("l_03", "l_07", "l_09", "l_10"):
        progress = build_progress(conn, learner_id)
        assert len(progress["checks"]) == 2, learner_id
        assert progress["words"], learner_id
        assert progress["wcpm_change"] > 0, learner_id


# --- Route ------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "route.db"
    seed_db(path)
    monkeypatch.setenv("BASA_DB_PATH", str(path))
    return path


def test_route_returns_the_comparison(db_path):
    with closing(connect(db_path)) as conn:
        save_check(conn, "a_1", {4: "misread"})
        save_check(conn, "a_2")
    r = client.get("/learners/l_07/progress")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"checks", "words", "wcpm_before", "wcpm_after", "wcpm_change"}
    assert [c["assessment_id"] for c in body["checks"]] == ["a_1", "a_2"]
    assert body["words"][4] == {"i": 4, "text": "palay", "before": "misread", "after": "matched"}
    assert body["wcpm_change"] == 2


def test_route_with_nothing_to_compare_is_the_empty_shape(db_path):
    r = client.get("/learners/l_01/progress")
    assert r.status_code == 200
    assert r.json() == empty_progress()


def test_route_unknown_learner_is_404(db_path):
    r = client.get("/learners/l_404/progress")
    assert r.status_code == 404
    assert "l_404" in r.json()["detail"]


def test_route_without_a_database_is_503(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "missing.db"))
    r = client.get("/learners/l_07/progress")
    assert r.status_code == 503
    assert not (tmp_path / "missing.db").exists()
