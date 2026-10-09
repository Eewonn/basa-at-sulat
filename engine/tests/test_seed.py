"""Tests for loading seed learners and passages (P0-BE2-2)."""

import json
from contextlib import closing

import pytest

from app import seed as seed_cli
from app.db import connect, init_db
from app.seed import (
    DEFAULT_LEARNERS_PATH,
    DEFAULT_PASSAGES_PATH,
    SeedError,
    load_entries,
    seed_db,
)

LEARNERS = [
    {"id": "l_01", "display_name": "A.R.", "grade": 1},
    {"id": "l_02", "display_name": "B.T.", "grade": 2},
]
PASSAGES = [
    {"id": "fil_g2_01", "title": "Ang Palay ni Lina", "language": "fil", "grade": 2,
     "text": "Nagtanim si Lina ng palay."},
    {"id": "eng_g2_01", "title": "Ben's Red Kite", "language": "eng", "grade": 2,
     "text": "Ben has a red kite."},
]


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def files(tmp_path):
    """Seed files in a temp folder, so tests can edit them freely."""
    return {
        "learners_path": write_json(tmp_path / "learners.json", LEARNERS),
        "passages_path": write_json(tmp_path / "passages.json", PASSAGES),
    }


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "seed.db"


def count(db_path, table):
    with closing(connect(db_path)) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def add_assessment(db_path, passage_id="fil_g2_01"):
    with closing(connect(db_path)) as conn, conn:
        conn.execute(
            "INSERT INTO assessments (id, learner_id, passage_id, duration_sec) "
            "VALUES ('a_01', 'l_01', ?, 30)",
            (passage_id,),
        )


# --- Happy paths -----------------------------------------------------------

def test_seeds_fresh_database(db_path, files):
    result = seed_db(db_path, **files)
    assert (result.learners_added, result.passages_added) == (2, 2)
    assert count(db_path, "learners") == 2
    assert count(db_path, "passages") == 2


def test_seeded_rows_match_the_json(db_path, files):
    seed_db(db_path, **files)
    with closing(connect(db_path)) as conn:
        row = conn.execute("SELECT * FROM passages WHERE id = 'fil_g2_01'").fetchone()
    assert (row["title"], row["language"], row["grade"], row["text"]) == (
        "Ang Palay ni Lina", "fil", 2, "Nagtanim si Lina ng palay."
    )


def test_seeds_into_existing_empty_database(db_path, files):
    init_db(db_path)
    assert seed_db(db_path, **files).learners_added == 2


def test_second_run_changes_nothing(db_path, files):
    seed_db(db_path, **files)
    result = seed_db(db_path, **files)
    assert result == seed_cli.SeedResult()  # all zeros
    assert count(db_path, "learners") == 2


def test_rerun_adds_new_entries(db_path, files):
    seed_db(db_path, **files)
    write_json(files["learners_path"], LEARNERS + [{"id": "l_03", "display_name": "C.M.", "grade": 3}])
    result = seed_db(db_path, **files)
    assert (result.learners_added, result.learners_updated) == (1, 0)


def test_rerun_updates_changed_learner(db_path, files):
    seed_db(db_path, **files)
    changed = [{**LEARNERS[0], "grade": 3}, LEARNERS[1]]
    write_json(files["learners_path"], changed)

    assert seed_db(db_path, **files).learners_updated == 1
    with closing(connect(db_path)) as conn:
        assert conn.execute("SELECT grade FROM learners WHERE id = 'l_01'").fetchone()[0] == 3


def test_passage_text_can_change_when_unused(db_path, files):
    seed_db(db_path, **files)
    write_json(files["passages_path"], [{**PASSAGES[0], "text": "Bagong teksto."}, PASSAGES[1]])
    assert seed_db(db_path, **files).passages_updated == 1


def test_used_passage_can_change_title_but_not_text(db_path, files):
    seed_db(db_path, **files)
    add_assessment(db_path)
    write_json(files["passages_path"], [{**PASSAGES[0], "title": "Bagong Pamagat"}, PASSAGES[1]])
    assert seed_db(db_path, **files).passages_updated == 1


def test_extra_fields_are_ignored(db_path, files):
    write_json(files["passages_path"], [{**PASSAGES[0], "credit": "Written by a teammate"}])
    assert seed_db(db_path, **files).passages_added == 1


def test_regional_language_code_accepted(db_path, files):
    write_json(files["passages_path"], [{**PASSAGES[0], "id": "ilo_g2_01", "language": "ilo"}])
    assert seed_db(db_path, **files).passages_added == 1


def test_reset_wipes_existing_results(db_path, files):
    seed_db(db_path, **files)
    add_assessment(db_path)
    seed_db(db_path, reset=True, **files)
    assert count(db_path, "assessments") == 0
    assert count(db_path, "learners") == 2


def test_repo_seed_files_are_valid(db_path):
    """The real data/ files load cleanly and include learner l_07 from docs/API.md."""
    seed_db(db_path, learners_path=DEFAULT_LEARNERS_PATH, passages_path=DEFAULT_PASSAGES_PATH)
    with closing(connect(db_path)) as conn:
        assert conn.execute("SELECT 1 FROM learners WHERE id = 'l_07'").fetchone()
        languages = {row[0] for row in conn.execute("SELECT language FROM passages")}
    assert {"fil", "eng"} <= languages


# --- The text-change guard -------------------------------------------------

def test_text_change_on_used_passage_is_refused(db_path, files):
    seed_db(db_path, **files)
    add_assessment(db_path)
    write_json(files["passages_path"], [{**PASSAGES[0], "text": "Ibang teksto."}, PASSAGES[1]])

    with pytest.raises(SeedError, match="fil_g2_01"):
        seed_db(db_path, **files)

    with closing(connect(db_path)) as conn:
        text = conn.execute("SELECT text FROM passages WHERE id = 'fil_g2_01'").fetchone()[0]
    assert text == PASSAGES[0]["text"]


def test_refused_run_writes_nothing_at_all(db_path, files):
    """Valid changes in the same run are rolled back with the refused one."""
    seed_db(db_path, **files)
    add_assessment(db_path)
    write_json(files["learners_path"], LEARNERS + [{"id": "l_03", "display_name": "C.M.", "grade": 3}])
    write_json(files["passages_path"], [{**PASSAGES[0], "text": "Ibang teksto."}, PASSAGES[1]])

    with pytest.raises(SeedError):
        seed_db(db_path, **files)
    assert count(db_path, "learners") == 2


# --- Bad input -------------------------------------------------------------

@pytest.mark.parametrize("bad_entry, message", [
    ({"id": "l_09", "grade": 2}, "missing display_name"),
    ({"id": "l_09", "display_name": "  ", "grade": 2}, "display_name"),
    ({"id": "", "display_name": "A.B.", "grade": 2}, "'id'"),
    ({"id": 9, "display_name": "A.B.", "grade": 2}, "'id'"),
    ({"id": "l_09", "display_name": "A.B.", "grade": 0}, "grade"),
    ({"id": "l_09", "display_name": "A.B.", "grade": 13}, "grade"),
    ({"id": "l_09", "display_name": "A.B.", "grade": "2"}, "grade"),
    ({"id": "l_09", "display_name": "A.B.", "grade": True}, "grade"),
    ({"id": "l_09", "display_name": "A.B.", "grade": 2.5}, "grade"),
])
def test_bad_learner_rejected(db_path, files, bad_entry, message):
    write_json(files["learners_path"], LEARNERS + [bad_entry])
    with pytest.raises(SeedError, match=message):
        seed_db(db_path, **files)


@pytest.mark.parametrize("change, message", [
    ({"text": ""}, "'text'"),
    ({"title": None}, "'title'"),
    ({"language": "Filipino"}, "language"),
    ({"language": "FIL"}, "language"),
    ({"grade": -1}, "grade"),
])
def test_bad_passage_rejected(db_path, files, change, message):
    write_json(files["passages_path"], [{**PASSAGES[0], **change}])
    with pytest.raises(SeedError, match=message):
        seed_db(db_path, **files)


def test_duplicate_id_rejected(db_path, files):
    write_json(files["learners_path"], LEARNERS + [LEARNERS[0]])
    with pytest.raises(SeedError, match="duplicate id 'l_01'"):
        seed_db(db_path, **files)


def test_invalid_json_rejected(db_path, files):
    files["passages_path"].write_text("[{", encoding="utf-8")
    with pytest.raises(SeedError, match="invalid JSON"):
        seed_db(db_path, **files)


@pytest.mark.parametrize("data", [{"id": "l_01"}, ["l_01"]])
def test_wrong_json_shape_rejected(tmp_path, data):
    path = write_json(tmp_path / "shape.json", data)
    with pytest.raises(SeedError):
        load_entries(path)


def test_missing_file_rejected(db_path, files, tmp_path):
    files["learners_path"] = tmp_path / "nope.json"
    with pytest.raises(SeedError, match="file not found"):
        seed_db(db_path, **files)


def test_empty_lists_are_allowed(db_path, files):
    write_json(files["learners_path"], [])
    write_json(files["passages_path"], [])
    assert seed_db(db_path, **files) == seed_cli.SeedResult()


def test_bad_input_creates_no_database(db_path, files):
    write_json(files["learners_path"], [{"id": "l_01"}])
    with pytest.raises(SeedError):
        seed_db(db_path, **files)
    assert not db_path.exists()


def test_bad_input_with_reset_keeps_existing_data(db_path, files):
    """Validation runs before --reset, so a typo can't wipe the database."""
    seed_db(db_path, **files)
    add_assessment(db_path)
    write_json(files["learners_path"], [{"id": "l_01"}])

    with pytest.raises(SeedError):
        seed_db(db_path, reset=True, **files)
    assert count(db_path, "assessments") == 1


# --- Command-line script ---------------------------------------------------

def test_cli_seeds_and_reports_counts(db_path, capsys):
    assert seed_cli.main(["--path", str(db_path)]) == 0
    out = capsys.readouterr().out
    assert "Learners: 10 added" in out
    assert f"Passages: {len(load_entries(DEFAULT_PASSAGES_PATH))} added" in out  # grows as passages are added


def test_cli_rerun_succeeds(db_path):
    assert seed_cli.main(["--path", str(db_path)]) == 0
    assert seed_cli.main(["--path", str(db_path)]) == 0


def test_cli_reset_succeeds(db_path):
    assert seed_cli.main(["--path", str(db_path)]) == 0
    assert seed_cli.main(["--path", str(db_path), "--reset"]) == 0


def test_cli_reports_bad_data_cleanly(db_path, tmp_path, monkeypatch, capsys):
    bad = write_json(tmp_path / "bad.json", [{"id": "l_01"}])
    monkeypatch.setattr(seed_cli, "DEFAULT_LEARNERS_PATH", bad)

    assert seed_cli.main(["--path", str(db_path)]) == 1
    assert "missing display_name" in capsys.readouterr().err
