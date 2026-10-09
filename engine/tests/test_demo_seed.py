"""Tests for the demo Basa checks (python -m app.seed --demo)."""

import json
from contextlib import closing

import pytest

from app import seed as seed_cli
from app.assessments import save_assessment
from app.db import connect
from app.demo_seed import (
    DemoSeedError,
    load_demo_checks,
    prepare_demo_checks,
)
from app.seed import DATA_DIR, DEFAULT_DEMO_CHECKS_DIR, DEFAULT_DEMO_CONFIG_PATH, seed_db

# fil_g2_01 has 23 words. The fake source reads every word in 0.5 s, so the
# whole reading takes 11.5 s (120 WCPM when every word is matched).
PASSAGE_ID = "fil_g2_01"


def passage_words():
    passages = json.loads((DATA_DIR / "passages" / "passages.json").read_text(encoding="utf-8"))
    text = next(p["text"] for p in passages if p["id"] == PASSAGE_ID)
    return text.split()


def make_source(flagged=()):
    words = [
        {"i": i, "text": text, "label": "misread" if i in flagged else "matched",
         "score": 0.9, "start": i * 0.5, "end": i * 0.5 + 0.4}
        for i, text in enumerate(passage_words())
    ]
    return {"recording_id": "rec_1", "passage_id": PASSAGE_ID, "duration_sec": 11.5,
            "words": words, "pauses": [{"before_word": 5, "seconds": 1.0}]}


def entry(**overrides):
    base = {"id": "demo_a", "source": "rec_1", "learner_id": "l_01",
            "checked_at": "2026-09-07T01:00:00Z"}
    base.update(overrides)
    return base


@pytest.fixture
def checks_dir(tmp_path):
    folder = tmp_path / "checks"
    folder.mkdir()
    (folder / "rec_1.json").write_text(json.dumps(make_source()), encoding="utf-8")
    return folder


@pytest.fixture
def write_config(tmp_path):
    def write(*entries):
        path = tmp_path / "demo_seed.json"
        path.write_text(json.dumps({"checks": list(entries)}), encoding="utf-8")
        return path
    return write


@pytest.fixture
def prepare(checks_dir, write_config):
    """Prepare the given config entries against the fake source."""
    def run(*entries):
        return prepare_demo_checks(write_config(*entries), checks_dir)
    return run


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    seed_db(db_path)
    connection = connect(db_path)
    yield connection
    connection.close()


def ids(conn):
    return [row["id"] for row in conn.execute("SELECT id FROM assessments ORDER BY id")]


# --- Preparing: durations and timing --------------------------------------

def test_no_duration_setting_keeps_the_source(prepare):
    (check,) = prepare(entry())
    assert check.result["duration_sec"] == 11.5
    assert check.result["words"][1]["start"] == 0.5


def test_target_wcpm_slows_the_check_and_scales_times(prepare):
    # 23 correct words at 46 WCPM take 30 s, so every time is stretched by 30/11.5.
    (check,) = prepare(entry(target_wcpm=46))
    result = check.result
    assert result["duration_sec"] == 30.0
    factor = 30 / 11.5
    assert result["words"][22]["end"] == round((22 * 0.5 + 0.4) * factor, 2)
    assert result["pauses"][0]["seconds"] == round(1.0 * factor, 2)
    assert all(word["end"] <= result["duration_sec"] for word in result["words"])


def test_duration_sec_sets_the_duration_directly(prepare):
    (check,) = prepare(entry(duration_sec=23))
    assert check.result["duration_sec"] == 23.0
    assert check.result["words"][1]["start"] == 1.0  # 0.5 s doubled


def test_null_word_times_stay_null(checks_dir, write_config):
    source = make_source()
    source["words"][3]["start"] = source["words"][3]["end"] = None
    (checks_dir / "rec_1.json").write_text(json.dumps(source), encoding="utf-8")
    (check,) = prepare_demo_checks(write_config(entry(target_wcpm=46)), checks_dir)
    assert (check.result["words"][3]["start"], check.result["words"][3]["end"]) == (None, None)


def test_source_file_is_not_changed(checks_dir, prepare):
    before = (checks_dir / "rec_1.json").read_text(encoding="utf-8")
    prepare(entry(target_wcpm=46, relabel={"skipped": [0]}))
    assert (checks_dir / "rec_1.json").read_text(encoding="utf-8") == before


def test_timestamps_use_the_schema_format_and_confirm_after(prepare):
    (check,) = prepare(entry(checked_at="2026-09-07T09:00:00+08:00"))
    assert check.created_at == "2026-09-07T01:00:00.000Z"
    assert check.confirmed_at == "2026-09-07T01:05:00.000Z"


# --- Preparing: hand relabels ----------------------------------------------

def test_relabel_changes_labels_and_caps_scores(prepare):
    (check,) = prepare(entry(relabel={"misread": [0], "skipped": [1, 2]}))
    words = check.result["words"]
    assert [(w["label"], w["score"]) for w in words[:3]] == [
        ("misread", 0.3), ("skipped", 0.05), ("skipped", 0.05)
    ]
    assert words[3]["label"] == "matched"


def test_relabel_never_raises_a_score(checks_dir, write_config):
    source = make_source()
    source["words"][0]["score"] = 0.01
    (checks_dir / "rec_1.json").write_text(json.dumps(source), encoding="utf-8")
    (check,) = prepare_demo_checks(write_config(entry(relabel={"misread": [0]})), checks_dir)
    assert check.result["words"][0]["score"] == 0.01


def test_target_wcpm_counts_words_after_relabel(prepare):
    # 13 matched words at 26 WCPM take 30 s.
    (check,) = prepare(entry(target_wcpm=26, relabel={"skipped": list(range(10))}))
    assert check.result["duration_sec"] == 30.0


@pytest.mark.parametrize(
    ("relabel", "message"),
    [
        ({"matched": [0]}, "only relabel to misread or skipped"),
        ({"skipped": 3}, "must be a list"),
        ({"skipped": [99]}, "index 99"),
        ({"skipped": [True]}, "index True"),
        ({"skipped": [1], "misread": [1]}, "relabeled twice"),
        (["skipped"], "must map a label"),
    ],
)
def test_bad_relabel_is_rejected(prepare, relabel, message):
    with pytest.raises(DemoSeedError, match=message):
        prepare(entry(relabel=relabel))


# --- Preparing: config errors -----------------------------------------------

@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"id": "a_1"}, "must start with 'demo_'"),
        ({"target_wcpm": 40, "duration_sec": 30}, "not both"),
        ({"target_wcpm": 0}, "target_wcpm"),
        ({"target_wcpm": True}, "target_wcpm"),
        ({"duration_sec": -1}, "duration_sec"),
        ({"checked_at": "2026-09-07T01:00:00"}, "needs a timezone"),
        ({"checked_at": "yesterday"}, "not a valid timestamp"),
        ({"source": "missing"}, "file not found"),
    ],
)
def test_bad_entry_is_rejected(prepare, overrides, message):
    with pytest.raises(DemoSeedError, match=message):
        prepare(entry(**overrides))


def test_target_wcpm_with_no_matched_words_is_rejected(prepare):
    with pytest.raises(DemoSeedError, match="use duration_sec"):
        prepare(entry(target_wcpm=10, relabel={"skipped": list(range(23))}))


def test_missing_field_is_rejected(prepare):
    bad = entry()
    del bad["learner_id"]
    with pytest.raises(DemoSeedError, match="missing learner_id"):
        prepare(bad)


def test_duplicate_id_is_rejected(prepare):
    with pytest.raises(DemoSeedError, match="duplicate id 'demo_a'"):
        prepare(entry(), entry())


@pytest.mark.parametrize("content", ['{"checks": []}', "[]", "{not json"])
def test_bad_config_file_is_rejected(tmp_path, checks_dir, content):
    path = tmp_path / "demo_seed.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(DemoSeedError):
        prepare_demo_checks(path, checks_dir)


# --- Loading -----------------------------------------------------------------

def test_load_saves_confirmed_checks_with_their_times(conn, prepare):
    outcome = load_demo_checks(conn, prepare(entry(target_wcpm=46)))
    assert (outcome.loaded, outcome.replaced, outcome.level_mismatches) == (1, 0, [])
    row = conn.execute(
        "SELECT status, keep_audio, audio_path, wcpm, level, created_at, confirmed_at "
        "FROM assessments WHERE id = 'demo_a'"
    ).fetchone()
    assert tuple(row) == (
        "confirmed", 0, None, 46, "At Grade Level",
        "2026-09-07T01:00:00.000Z", "2026-09-07T01:05:00.000Z",
    )


def test_relabeled_check_reaches_a_lower_level(conn, prepare):
    # 13 of 23 words (57%) is Developing.
    checks = prepare(entry(target_wcpm=26, relabel={"skipped": list(range(10))}))
    load_demo_checks(conn, checks)
    assert conn.execute("SELECT level FROM assessments").fetchone()["level"] == "Developing"


def test_rerun_replaces_demo_checks_instead_of_duplicating(conn, prepare):
    load_demo_checks(conn, prepare(entry(id="demo_a"), entry(id="demo_b")))
    outcome = load_demo_checks(conn, prepare(entry(id="demo_a")))
    assert (outcome.loaded, outcome.replaced) == (1, 2)
    assert ids(conn) == ["demo_a"]


def test_real_checks_are_never_touched(conn, prepare):
    # "demoXa" would match a LIKE 'demo_%' that forgot to escape the underscore.
    for real_id in ("a_real", "demoXa"):
        result = make_source()
        del result["recording_id"]
        save_assessment(conn, {**result, "assessment_id": real_id, "learner_id": "l_01"})
    load_demo_checks(conn, prepare(entry(id="demo_a")))
    load_demo_checks(conn, prepare(entry(id="demo_a")))
    assert ids(conn) == ["a_real", "demoXa", "demo_a"]


def test_rerun_removes_practice_on_demo_checks(conn, prepare):
    load_demo_checks(conn, prepare(entry()))
    conn.execute(
        "INSERT INTO practice_attempts (learner_id, assessment_id, word, result, score) "
        "VALUES ('l_01', 'demo_a', 'palay', 'match', 0.9)"
    )
    conn.commit()
    outcome = load_demo_checks(conn, prepare(entry()))
    assert outcome.practice_removed == 1


def test_invalid_check_fails_before_old_demo_checks_are_deleted(conn, prepare):
    load_demo_checks(conn, prepare(entry(id="demo_old")))
    checks = prepare(entry(id="demo_new", learner_id="l_404"))
    with pytest.raises(DemoSeedError, match="unknown learner 'l_404'"):
        load_demo_checks(conn, checks)
    assert ids(conn) == ["demo_old"]


def test_level_mismatch_is_reported(conn, prepare):
    outcome = load_demo_checks(conn, prepare(entry(expected_level="Low Emerging")))
    assert outcome.level_mismatches == [
        "demo_a: expected Low Emerging, got At Grade Level"
    ]


# --- Command line ------------------------------------------------------------

def test_cli_demo_seeds_and_reports(tmp_path, checks_dir, write_config, monkeypatch, capsys):
    monkeypatch.setattr(seed_cli, "DEFAULT_DEMO_CONFIG_PATH", write_config(entry()))
    db_path = tmp_path / "cli.db"
    args = ["--path", str(db_path), "--demo", "--demo-checks", str(checks_dir)]
    assert seed_cli.main(args) == 0
    assert "Demo checks: 1 loaded" in capsys.readouterr().out
    with closing(connect(db_path)) as conn:
        assert ids(conn) == ["demo_a"]


def test_cli_bad_demo_config_fails_before_reset(tmp_path, checks_dir, write_config,
                                                 monkeypatch, capsys):
    db_path = tmp_path / "cli.db"
    seed_db(db_path)
    with closing(connect(db_path)) as conn:
        conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_keep', 'Z.Z.', 1)")
        conn.commit()
    monkeypatch.setattr(seed_cli, "DEFAULT_DEMO_CONFIG_PATH", write_config(entry(id="bad")))
    args = ["--path", str(db_path), "--reset", "--demo", "--demo-checks", str(checks_dir)]
    assert seed_cli.main(args) == 1
    assert "must start with 'demo_'" in capsys.readouterr().err
    with closing(connect(db_path)) as conn:
        assert conn.execute("SELECT 1 FROM learners WHERE id = 'l_keep'").fetchone()


def test_cli_without_demo_loads_no_checks(tmp_path):
    db_path = tmp_path / "cli.db"
    assert seed_cli.main(["--path", str(db_path)]) == 0
    with closing(connect(db_path)) as conn:
        assert ids(conn) == []


# --- The real config -----------------------------------------------------------

@pytest.mark.skipif(
    not DEFAULT_DEMO_CHECKS_DIR.is_dir(),
    reason="needs the score() results in data/demo_checks/",
)
def test_real_demo_config_loads_every_check_at_its_expected_level(conn):
    checks = prepare_demo_checks(DEFAULT_DEMO_CONFIG_PATH, DEFAULT_DEMO_CHECKS_DIR)
    outcome = load_demo_checks(conn, checks)
    assert outcome.level_mismatches == []
    levels = {row["level"] for row in conn.execute("SELECT level FROM assessments")}
    # The point of the demo data: every level shows up at least once.
    assert levels == {
        "Low Emerging", "High Emerging", "Developing", "Transitioning", "At Grade Level"
    }
