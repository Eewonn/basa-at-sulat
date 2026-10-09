"""Tests for the class view (P2-BE2-3): app/class_view.py, GET /class and GET /class/export.csv."""

import csv
import io
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.assessments import confirm_assessment, override_word
from app.class_view import (
    EXPORT_COLUMNS,
    MAX_COMMON_WORDS,
    build_class,
    common_missed_words,
    export_csv,
    export_rows,
)
from app.db import connect
from app.main import app
from app.plans import PlanError
from app.seed import seed_db

# Helpers for a check on fil_g2_01 (indices are listed in test_practice.py):
# 4 palay, 6 bukid., 13 lolo., 18 mangga.
from tests.test_practice import save_check, set_times

client = TestClient(app)


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    seed_db(path)
    with closing(connect(path)) as conn:
        yield conn


@pytest.fixture(autouse=True)
def plans(monkeypatch):
    """Never call Ollama: record each group asked for and return a fake plan."""
    asked = []

    def fake_get_plan(group, refresh=False):
        group.refresh = refresh  # recorded for the refresh tests
        asked.append(group)
        return f"plan for {group.level}"

    monkeypatch.setattr("app.class_view.get_plan", fake_get_plan)
    return asked


def set_level(conn, assessment_id, level):
    with conn:
        conn.execute("UPDATE assessments SET level = ? WHERE id = ?", (level, assessment_id))


def check(conn, assessment_id, learner_id, missed=(), level="Developing", **kwargs):
    save_check(conn, assessment_id, missed, learner_id=learner_id, **kwargs)
    set_level(conn, assessment_id, level)


def passage_text(conn, passage_id):
    return conn.execute("SELECT text FROM passages WHERE id = ?", (passage_id,)).fetchone()["text"]


def group(result, level):
    return next(g for g in result["groups"] if g["level"] == level)


# --- Grouping --------------------------------------------------------------

def test_empty_class_has_no_groups(conn, plans):
    assert build_class(conn) == {"groups": []}
    assert plans == []


def test_learners_are_grouped_by_level_lowest_first(conn):
    check(conn, "a_1", "l_01", level="Developing")
    check(conn, "a_2", "l_02", level="Low Emerging")
    check(conn, "a_3", "l_03", level="Developing")
    check(conn, "a_4", "l_04", level="At Grade Level")

    result = build_class(conn)

    assert [g["level"] for g in result["groups"]] == ["Low Emerging", "Developing", "At Grade Level"]
    assert group(result, "Developing")["learner_ids"] == ["l_01", "l_03"]
    assert group(result, "Developing")["draft_plan"] == "plan for Developing"


def test_a_learner_is_grouped_by_their_latest_confirmed_check(conn):
    check(conn, "a_old", "l_01", level="Low Emerging")
    set_times(conn, "a_old", "2026-09-01T00:00:00.000Z")
    check(conn, "a_new", "l_01", level="Transitioning")
    set_times(conn, "a_new", "2026-10-01T00:00:00.000Z")

    assert [g["level"] for g in build_class(conn)["groups"]] == ["Transitioning"]


def test_drafts_and_unchecked_learners_are_left_out(conn):
    check(conn, "a_1", "l_01")
    save_check(conn, "a_draft", learner_id="l_02", confirm=False)

    groups = build_class(conn)["groups"]

    assert [g["learner_ids"] for g in groups] == [["l_01"]]


def test_a_check_without_a_level_is_left_out_and_logged(conn, caplog):
    check(conn, "a_1", "l_01")
    set_level(conn, "a_1", None)

    assert build_class(conn) == {"groups": []}
    assert "a_1 has no level" in caplog.text


def test_an_unknown_level_name_goes_after_the_crla_levels(conn):
    check(conn, "a_1", "l_01", level="Zzz")
    check(conn, "a_2", "l_02", level="Low Emerging")
    assert [g["level"] for g in build_class(conn)["groups"]] == ["Low Emerging", "Zzz"]


# --- Common missed words ---------------------------------------------------

def test_a_word_needs_two_learners_to_be_common(conn):
    check(conn, "a_1", "l_01", {4: "misread", 13: "skipped"})
    check(conn, "a_2", "l_02", {4: "skipped"})

    assert build_class(conn)["groups"][0]["common_missed_words"] == ["palay"]


def test_words_are_ranked_by_how_many_learners_missed_them(conn):
    check(conn, "a_1", "l_01", {4: "misread", 18: "misread"})
    check(conn, "a_2", "l_02", {4: "misread", 18: "misread"})
    check(conn, "a_3", "l_03", {18: "misread", 13: "misread"})
    check(conn, "a_4", "l_04", {13: "misread"})

    # mangga: 3 learners; palay and lolo: 2 each, palay first in the passage.
    assert build_class(conn)["groups"][0]["common_missed_words"] == ["mangga", "palay", "lolo"]


def test_a_word_missed_twice_by_one_learner_counts_once(conn):
    # "ng" is at 3, 11, 17 and 21 in fil_g2_01.
    check(conn, "a_1", "l_01", {3: "misread", 11: "misread"})
    check(conn, "a_2", "l_02")
    assert build_class(conn)["groups"][0]["common_missed_words"] == []


def test_punctuation_and_case_dont_split_a_word(conn):
    check(conn, "a_1", "l_01", {6: "misread"})  # "bukid."
    check(conn, "a_2", "l_02", {6: "skipped"})
    assert build_class(conn)["groups"][0]["common_missed_words"] == ["bukid"]


def test_matched_words_and_teacher_overrides_use_final_labels(conn):
    check(conn, "a_1", "l_01", {4: "misread"}, confirm=False)
    override_word(conn, "a_1", 4, "matched")
    confirm_assessment(conn, "a_1")
    set_level(conn, "a_1", "Developing")
    check(conn, "a_2", "l_02", {4: "misread"})

    assert build_class(conn)["groups"][0]["common_missed_words"] == []


def test_the_list_is_capped(conn):
    missed = {i: "misread" for i in (0, 2, 4, 7, 9, 12, 15, 18)}
    check(conn, "a_1", "l_01", missed)
    check(conn, "a_2", "l_02", missed)

    words = build_class(conn)["groups"][0]["common_missed_words"]

    assert len(words) == MAX_COMMON_WORDS
    assert words == ["Nagtanim", "Lina", "palay", "Masaya", "Tinulungan"]


def test_the_most_common_spelling_is_shown(conn):
    text = passage_text(conn, "fil_g2_01")
    capitalised = text.replace("ng palay", "ng Palay")
    with conn:
        conn.execute(
            "INSERT INTO passages (id, title, language, grade, text) VALUES ('fil_x', 'X', 'fil', 2, ?)",
            (capitalised,),
        )
    check(conn, "a_1", "l_01", {4: "misread"}, passage_id="fil_x", text=capitalised)
    check(conn, "a_2", "l_02", {4: "misread"})
    check(conn, "a_3", "l_03", {4: "misread"})

    assert build_class(conn)["groups"][0]["common_missed_words"] == ["palay"]


def test_a_group_of_one_gets_that_childs_own_missed_words(conn):
    check(conn, "a_1", "l_01", {18: "misread", 4: "misread", 13: "skipped"}, level="Low Emerging")
    check(conn, "a_2", "l_02", {4: "misread"}, level="Developing")
    check(conn, "a_3", "l_03", {13: "misread"}, level="Developing")

    result = build_class(conn)

    assert group(result, "Low Emerging")["common_missed_words"] == ["palay", "lolo", "mangga"]
    assert group(result, "Developing")["common_missed_words"] == []  # 2 learners: 2 needed


def test_a_group_of_one_is_capped_too(conn):
    check(conn, "a_1", "l_01", {i: "misread" for i in (0, 2, 4, 7, 9, 12, 15, 18)})
    assert build_class(conn)["groups"][0]["common_missed_words"] == [
        "Nagtanim", "Lina", "palay", "Masaya", "Tinulungan"]


def test_one_filipino_check_in_a_mixed_group_uses_that_childs_words(conn):
    eng = passage_text(conn, "eng_g2_01")
    check(conn, "a_1", "l_01", {0: "misread"}, passage_id="eng_g2_01", text=eng)
    check(conn, "a_2", "l_02", {4: "misread"})
    assert build_class(conn)["groups"][0]["common_missed_words"] == ["palay"]


def test_common_missed_words_with_no_checks_is_empty(conn):
    assert common_missed_words(conn, []) == []


# --- Plans -----------------------------------------------------------------

def test_the_plan_gets_the_group_stats_in_filipino(conn, plans):
    check(conn, "a_1", "l_01", {4: "misread"})
    check(conn, "a_2", "l_02", {4: "misread"})

    build_class(conn)

    assert len(plans) == 1
    assert plans[0].level == "Developing"
    assert plans[0].learner_count == 2
    assert plans[0].common_missed_words == ["palay"]
    assert plans[0].language == "fil"


def test_english_checks_never_reach_the_model(conn, plans):
    eng = passage_text(conn, "eng_g2_01")
    check(conn, "a_1", "l_01", {0: "misread"}, passage_id="eng_g2_01", text=eng)
    check(conn, "a_2", "l_02", {0: "misread"}, passage_id="eng_g2_01", text=eng)

    result = build_class(conn)

    assert plans == []
    assert result["groups"] == [{
        "level": "Developing", "learner_ids": ["l_01", "l_02"],
        "common_missed_words": [], "draft_plan": None,
    }]


def test_in_a_mixed_group_only_filipino_words_count(conn, plans):
    eng = passage_text(conn, "eng_g2_01")
    check(conn, "a_1", "l_01", {0: "misread"}, passage_id="eng_g2_01", text=eng)
    check(conn, "a_2", "l_02", {0: "misread"}, passage_id="eng_g2_01", text=eng)
    check(conn, "a_3", "l_03", {4: "misread"})
    check(conn, "a_4", "l_04", {4: "misread"})

    result = build_class(conn)

    assert group(result, "Developing")["common_missed_words"] == ["palay"]
    assert group(result, "Developing")["learner_ids"] == ["l_01", "l_02", "l_03", "l_04"]
    assert plans[0].learner_count == 4  # the plan is for the whole group


def test_plans_come_from_the_cache_unless_refresh_is_asked(conn, plans):
    check(conn, "a_1", "l_01")
    build_class(conn)
    build_class(conn, refresh=True)
    assert [g.refresh for g in plans] == [False, True]


def test_a_broken_template_gives_a_null_plan_not_an_error(conn, monkeypatch, caplog):
    def broken(group, refresh=False):
        raise PlanError("bad template")

    monkeypatch.setattr("app.class_view.get_plan", broken)
    check(conn, "a_1", "l_01")

    assert build_class(conn)["groups"][0]["draft_plan"] is None
    assert "bad template" in caplog.text


# --- Export ----------------------------------------------------------------

def test_export_has_a_row_for_every_learner(conn):
    check(conn, "a_1", "l_01", {4: "misread", 6: "skipped"}, level="Developing")
    set_times(conn, "a_1", "2026-10-05T03:00:00.000Z")

    rows = export_rows(conn)

    assert len(rows) == 10
    assert rows[0] == {
        "learner_id": "l_01", "display_name": "A.R.", "latest_check_date": "2026-10-05",
        "passage_title": rows[0]["passage_title"], "wcpm": rows[0]["wcpm"],
        "level": "Developing", "missed_count": 2,
    }
    assert rows[0]["passage_title"]
    assert rows[1] == {
        "learner_id": "l_02", "display_name": "B.T.", "latest_check_date": None,
        "passage_title": None, "wcpm": None, "level": None, "missed_count": None,
    }


def test_export_uses_the_latest_confirmed_check(conn):
    check(conn, "a_old", "l_01", {4: "misread"})
    set_times(conn, "a_old", "2026-09-01T00:00:00.000Z")
    check(conn, "a_new", "l_01")
    set_times(conn, "a_new", "2026-10-01T00:00:00.000Z")
    save_check(conn, "a_draft", {4: "misread", 6: "misread"}, learner_id="l_01", confirm=False)

    row = export_rows(conn)[0]

    assert row["latest_check_date"] == "2026-10-01"
    assert row["missed_count"] == 0


def test_export_csv_has_a_bom_header_and_crlf(conn):
    text = export_csv(conn)

    assert text.startswith("﻿")
    assert text.splitlines()[0] == "﻿" + ",".join(EXPORT_COLUMNS)
    assert "\r\n" in text


def test_export_csv_stops_formulas_and_keeps_filipino_letters(conn):
    with conn:
        conn.execute("UPDATE learners SET display_name = '=HYPERLINK(\"x\")' WHERE id = 'l_01'")
        conn.execute("UPDATE learners SET display_name = 'Ñ.O., Jr.' WHERE id = 'l_02'")

    rows = list(csv.DictReader(io.StringIO(export_csv(conn).lstrip("﻿"))))

    assert rows[0]["display_name"] == "'=HYPERLINK(\"x\")"
    assert rows[1]["display_name"] == "Ñ.O., Jr."  # quoted, so the comma stays in one cell


# --- Routes ----------------------------------------------------------------

@pytest.fixture
def db_env(tmp_path, monkeypatch):
    path = tmp_path / "route.db"
    seed_db(path)
    monkeypatch.setenv("BASA_DB_PATH", str(path))
    with closing(connect(path)) as conn:
        yield conn


def test_get_class(db_env):
    check(db_env, "a_1", "l_01")

    r = client.get("/class")

    assert r.status_code == 200
    assert r.json()["groups"][0]["learner_ids"] == ["l_01"]


@pytest.mark.parametrize("query, refresh", [("", False), ("?refresh=1", True),
                                            ("?refresh=true", True), ("?refresh=0", False)])
def test_get_class_refresh(db_env, plans, query, refresh):
    check(db_env, "a_1", "l_01")
    assert client.get("/class" + query).status_code == 200
    assert plans[0].refresh is refresh


def test_get_class_bad_refresh_is_422(db_env):
    assert client.get("/class?refresh=maybe").status_code == 422


def test_get_export(db_env):
    r = client.get("/class/export.csv")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="basa-results.csv"' == r.headers["content-disposition"]
    assert r.content.startswith(b"\xef\xbb\xbf")
    assert r.content.decode("utf-8-sig").splitlines()[0] == ",".join(EXPORT_COLUMNS)


@pytest.mark.parametrize("path", ["/class", "/class/export.csv"])
def test_no_database_is_503(tmp_path, monkeypatch, path):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "missing.db"))
    assert client.get(path).status_code == 503
