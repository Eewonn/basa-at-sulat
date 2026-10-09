"""Tests for Sanay practice sets (P2-BE2-1): app/practice.py and GET /learners/{id}/practice."""

from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.assessments import confirm_assessment, override_word, save_assessment
from app.db import connect
from app.main import app
from app.practice import LearnerNotFoundError, build_practice_set, sentence_at
from app.seed import seed_db

client = TestClient(app)

# fil_g2_01, as the seed loads it. Indices used below:
#  0 Nagtanim  1 si  2 Lina  3 ng  4 palay  5 sa  6 bukid.  7 Masaya  8 siya.
#  9 Tinulungan  10 siya  11 ng  12 kanyang  13 lolo.  14 Pagkatapos,  15 kumain
#  16 sila  17 ng  18 mangga  19 sa  20 ilalim  21 ng  22 puno.
FIL_TEXT = ("Nagtanim si Lina ng palay sa bukid. Masaya siya. Tinulungan siya ng kanyang lolo. "
            "Pagkatapos, kumain sila ng mangga sa ilalim ng puno.")


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    seed_db(path)
    with closing(connect(path)) as conn:
        yield conn


def make_result(assessment_id, missed=(), learner_id="l_07", passage_id="fil_g2_01",
                text=FIL_TEXT):
    """A /assess result covering every word, matched except the given {index: label}."""
    missed = dict(missed)
    return {
        "assessment_id": assessment_id,
        "learner_id": learner_id,
        "passage_id": passage_id,
        "duration_sec": 30.0,
        "words": [
            {"i": i, "text": word, "label": missed.get(i, "matched"), "score": 0.9,
             "start": i * 0.5, "end": i * 0.5 + 0.4}
            for i, word in enumerate(text.split())
        ],
        "pauses": [],
    }


def save_check(conn, assessment_id, missed=(), confirm=True, **kwargs):
    save_assessment(conn, make_result(assessment_id, missed, **kwargs))
    if confirm:
        confirm_assessment(conn, assessment_id)


def set_times(conn, assessment_id, confirmed_at, created_at="2026-10-01T00:00:00.000Z"):
    with conn:
        conn.execute("UPDATE assessments SET confirmed_at = ?, created_at = ? WHERE id = ?",
                     (confirmed_at, created_at, assessment_id))


def add_book(conn, book_id, text, language="fil", created_at="2026-10-01T00:00:00.000Z",
             untimed=()):
    """A book with one timed entry per word; indices in `untimed` get zero-length times."""
    with conn:
        conn.execute(
            "INSERT INTO books (id, title, language, text, audio_path, created_at) "
            "VALUES (?, 'Kuwento', ?, ?, NULL, ?)",
            (book_id, language, text, created_at),
        )
        conn.executemany(
            "INSERT INTO book_words (book_id, i, text, start_sec, end_sec) VALUES (?, ?, ?, ?, ?)",
            [(book_id, i, word, i * 1.0, i * 1.0 if i in untimed else i * 1.0 + 0.5)
             for i, word in enumerate(text.split())],
        )


def words(items):
    return [item["word"] for item in items]


# --- Which words ------------------------------------------------------------

def test_missed_words_come_with_their_sentence_in_passage_order(conn):
    save_check(conn, "a_1", {11: "skipped", 4: "misread"})
    assert build_practice_set(conn, "l_07") == [
        {"word": "palay", "sentence": "Nagtanim si Lina ng palay sa bukid.",
         "book_id": None, "word_index": None},
        {"word": "ng", "sentence": "Tinulungan siya ng kanyang lolo.",
         "book_id": None, "word_index": None},
    ]


def test_a_check_with_no_misses_gives_an_empty_set(conn):
    save_check(conn, "a_1")
    assert build_practice_set(conn, "l_07") == []


def test_punctuation_is_stripped_from_the_word_but_kept_in_the_sentence(conn):
    save_check(conn, "a_1", {14: "misread", 22: "skipped"})
    items = build_practice_set(conn, "l_07")
    assert words(items) == ["Pagkatapos", "puno"]
    assert items[0]["sentence"] == "Pagkatapos, kumain sila ng mangga sa ilalim ng puno."


def test_a_repeated_word_appears_once_with_its_first_sentence(conn):
    # "siya." at 8 and "siya" at 10 are the same word; so are the four "ng".
    save_check(conn, "a_1", {8: "misread", 10: "skipped", 3: "skipped", 21: "misread"})
    items = build_practice_set(conn, "l_07")
    assert words(items) == ["ng", "siya"]
    assert items[0]["sentence"] == "Nagtanim si Lina ng palay sa bukid."
    assert items[1]["sentence"] == "Masaya siya."


def test_teacher_overrides_decide_what_counts_as_missed(conn):
    save_check(conn, "a_1", {4: "misread"}, confirm=False)
    override_word(conn, "a_1", 4, "matched")   # the AI was wrong: palay was read fine
    override_word(conn, "a_1", 2, "misread")   # and it missed a mistake on Lina
    confirm_assessment(conn, "a_1")
    assert words(build_practice_set(conn, "l_07")) == ["Lina"]


def test_works_for_english_passages_too(conn):
    text = ("Ben has a red kite. He runs to the hill with his sister. The wind is strong, "
            "and the kite flies high. They laugh and wave at the birds.")
    save_check(conn, "a_1", {4: "misread"}, passage_id="eng_g2_01", text=text)
    assert build_practice_set(conn, "l_07") == [
        {"word": "kite", "sentence": "Ben has a red kite.", "book_id": None, "word_index": None},
    ]


# --- Which check ------------------------------------------------------------

def test_unknown_learner_raises(conn):
    with pytest.raises(LearnerNotFoundError, match="l_404"):
        build_practice_set(conn, "l_404")


def test_learner_with_no_checks_gets_an_empty_set(conn):
    assert build_practice_set(conn, "l_01") == []


def test_drafts_are_not_practised(conn):
    save_check(conn, "a_draft", {4: "misread"}, confirm=False)
    assert build_practice_set(conn, "l_07") == []


def test_a_newer_draft_does_not_replace_the_latest_confirmed_check(conn):
    save_check(conn, "a_old", {4: "misread"})
    save_check(conn, "a_new", {2: "misread"}, confirm=False)
    assert words(build_practice_set(conn, "l_07")) == ["palay"]


def test_the_latest_confirmed_check_is_used(conn):
    save_check(conn, "a_old", {4: "misread"})
    save_check(conn, "a_new", {2: "misread"})
    set_times(conn, "a_old", "2026-10-01T08:00:00.000Z")
    set_times(conn, "a_new", "2026-10-08T08:00:00.000Z")
    assert words(build_practice_set(conn, "l_07")) == ["Lina"]


def test_latest_is_by_confirmation_time_not_by_id(conn):
    save_check(conn, "a_2", {4: "misread"})
    save_check(conn, "a_1", {2: "misread"})
    set_times(conn, "a_2", "2026-10-01T08:00:00.000Z")
    set_times(conn, "a_1", "2026-10-08T08:00:00.000Z")
    assert words(build_practice_set(conn, "l_07")) == ["Lina"]


def test_same_confirmation_time_falls_back_to_creation_time(conn):
    save_check(conn, "a_b", {4: "misread"})
    save_check(conn, "a_a", {2: "misread"})
    same = "2026-10-08T08:00:00.000Z"
    set_times(conn, "a_b", same, created_at="2026-10-08T07:00:00.000Z")
    set_times(conn, "a_a", same, created_at="2026-10-08T07:30:00.000Z")
    assert words(build_practice_set(conn, "l_07")) == ["Lina"]


def test_other_learners_checks_are_not_mixed_in(conn):
    save_check(conn, "a_1", {4: "misread"}, learner_id="l_01")
    assert build_practice_set(conn, "l_07") == []
    assert words(build_practice_set(conn, "l_01")) == ["palay"]


# --- Clips ------------------------------------------------------------------

def test_a_word_in_a_book_gets_that_clip(conn):
    add_book(conn, "b_1", "Ang palay ay ginto.")
    save_check(conn, "a_1", {4: "misread", 2: "misread"})
    items = build_practice_set(conn, "l_07")
    assert [(i["word"], i["book_id"], i["word_index"]) for i in items] == [
        ("Lina", None, None),        # no book has it
        ("palay", "b_1", 1),
    ]


def test_clip_matching_ignores_case_punctuation_and_accents(conn):
    add_book(conn, "b_1", "«Palay!» sigaw ni Lína.")
    save_check(conn, "a_1", {4: "misread", 2: "misread"})
    items = build_practice_set(conn, "l_07")
    assert [(i["word"], i["word_index"]) for i in items] == [("Lina", 3), ("palay", 0)]


def test_books_in_another_language_are_ignored(conn):
    add_book(conn, "b_eng", "The palay is gold.", language="eng")
    save_check(conn, "a_1", {4: "misread"})
    assert build_practice_set(conn, "l_07")[0]["book_id"] is None


def test_the_oldest_book_and_earliest_word_win(conn):
    add_book(conn, "b_new", "palay", created_at="2026-10-09T00:00:00.000Z")
    add_book(conn, "b_old", "Ang palay at palay.", created_at="2026-10-02T00:00:00.000Z")
    save_check(conn, "a_1", {4: "misread"})
    item = build_practice_set(conn, "l_07")[0]
    assert (item["book_id"], item["word_index"]) == ("b_old", 1)


def test_untimed_words_are_not_used_as_clips(conn):
    # Zero-length times would cut an empty clip, so the next timed "palay" is used.
    add_book(conn, "b_1", "palay at palay", untimed={0})
    save_check(conn, "a_1", {4: "misread"})
    item = build_practice_set(conn, "l_07")[0]
    assert (item["book_id"], item["word_index"]) == ("b_1", 2)


def test_untimed_only_means_no_clip(conn):
    add_book(conn, "b_1", "palay", untimed={0})
    save_check(conn, "a_1", {4: "misread"})
    assert build_practice_set(conn, "l_07")[0]["book_id"] is None


# --- Sentences --------------------------------------------------------------

@pytest.mark.parametrize("text, i, expected", [
    ("Isa. Dalawa tatlo. Apat", 3, "Apat"),                        # last sentence has no full stop
    ("Isa. Dalawa tatlo. Apat", 1, "Dalawa tatlo."),
    ("Isa", 0, "Isa"),                                             # one word, no punctuation
    # Dialogue: "!" before a lowercase word doesn't end the sentence.
    ('"Tara na!" sabi niya. Umalis sila.', 0, '"Tara na!" sabi niya.'),
    ('"Tara na!" sabi niya. Umalis sila.', 4, "Umalis sila."),
    ('Sabi niya, "Tara na!" Umalis sila.', 3, 'Sabi niya, "Tara na!"'),  # closing quote after "!"
    ("Saan ka pupunta? Sa bahay.", 1, "Saan ka pupunta?"),
    ("Ay naku… Sige na.", 3, "Sige na."),
    ("Pagkatapos, kumain sila.", 0, "Pagkatapos, kumain sila."),   # a comma doesn't end a sentence
])
def test_sentence_at(text, i, expected):
    assert sentence_at(text.split(), i) == expected


# --- Route ------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "route.db"
    seed_db(path)
    monkeypatch.setenv("BASA_DB_PATH", str(path))
    return path


def test_route_returns_items(db_path):
    with closing(connect(db_path)) as conn:
        add_book(conn, "b_1", "Ang palay ay ginto.")
        save_check(conn, "a_1", {4: "misread"})
    r = client.get("/learners/l_07/practice")
    assert r.status_code == 200
    assert r.json() == {"items": [
        {"word": "palay", "sentence": "Nagtanim si Lina ng palay sa bukid.",
         "book_id": "b_1", "word_index": 1},
    ]}


def test_route_with_no_confirmed_check_is_an_empty_list(db_path):
    r = client.get("/learners/l_01/practice")
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_route_unknown_learner_is_404(db_path):
    r = client.get("/learners/l_404/practice")
    assert r.status_code == 404
    assert "l_404" in r.json()["detail"]


def test_route_without_a_database_is_503(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "missing.db"))
    r = client.get("/learners/l_07/practice")
    assert r.status_code == 503
    assert not (tmp_path / "missing.db").exists()
