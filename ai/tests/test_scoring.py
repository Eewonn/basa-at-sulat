"""score() labelling, timing and pauses, driven by canned alignments (no model needed)."""

import pytest

from ai import aligner, scoring
from ai.aligner import Alignment, WordAlignment


def fake(words, frame_sec=0.02, duration=10.0):
    return Alignment(words=words, frame_sec=frame_sec, duration_sec=duration)


def wa(start, end, scores):
    return WordAlignment(start_frame=start, end_frame=end, token_scores=scores)


# --- word_score ---------------------------------------------------------------

@pytest.mark.parametrize(
    "letter_probs, expected",
    [
        ([1.0, 1.0], 1.0),
        ([0.9, 0.01], 0.5),
        ([0.99, 0.95, 0.001], 0.25),  # 1-in-1000: exactly the flag cutoff
        ([0.5, 1e-4], 0.0),
        ([0.5, 0.0], 0.0),  # zero doesn't crash the log
    ],
)
def test_word_score_maps_the_weakest_letter_to_a_log_scale(letter_probs, expected):
    assert scoring.word_score(letter_probs) == pytest.approx(expected)


def test_one_bad_letter_flags_a_word_the_average_would_pass():
    # palay said as "pala": four letters fit perfectly, the "y" has nothing behind it
    near_miss = [0.99, 0.98, 0.99, 0.97, 1e-5]
    assert sum(near_miss) / len(near_miss) > 0.75  # the old average-based score called this a match
    assert scoring.label_word(scoring.word_score(near_miss), 5, 3.0) == "misread"


# --- label_word -------------------------------------------------------------

@pytest.mark.parametrize(
    "score, n_chars, fpc, expected",
    [
        (0.95, 5, 3.0, "matched"),
        (0.26, 5, 3.0, "matched"),
        (0.25, 5, 3.0, "misread"),  # at the cutoff is flagged
        (0.0, 5, 3.0, "misread"),  # a letter that doesn't fit, with a normal duration: said something else
        (0.0, 3, 1.0, "skipped"),  # no fit and squeezed to one frame per letter
        (0.2, 4, 1.2, "skipped"),
        (0.0, 1, 1.0, "misread"),  # a one-letter word is always 1 frame/letter: can't be "skipped"
        (0.9, 4, 1.0, "matched"),  # short but clearly there (fast reader): not a skip
    ],
)
def test_label_word(score, n_chars, fpc, expected):
    assert scoring.label_word(score, n_chars, fpc) == expected


# --- score() with canned alignments -----------------------------------------

PASSAGE = "Ben has a red kite"  # ben / has / a / red / kite


def canned():
    return fake([
        wa(10, 16, [0.9, 0.9, 0.9]),  # Ben: fits
        wa(20, 29, [0.9, 0.0005, 0.9]),  # has: one letter doesn't fit, normal length
        wa(30, 31, [0.0]),  # a: nothing, but one letter
        wa(40, 43, [0.0, 0.0, 0.0]),  # red: squeezed, nothing
        wa(200, 212, [0.95, 0.9, 0.92, 0.9]),  # kite: fits, after a long gap
    ])


def test_score_labels_and_numbers(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: canned())
    result = scoring.score("any.wav", PASSAGE)
    assert [w["label"] for w in result["words"]] == ["matched", "misread", "misread", "skipped", "matched"]
    assert [w["i"] for w in result["words"]] == [0, 1, 2, 3, 4]
    assert [w["text"] for w in result["words"]] == PASSAGE.split()
    ben = result["words"][0]
    assert ben["score"] == 0.99 and ben["start"] == 0.2 and ben["end"] == 0.32  # 1 + log10(0.9)/4


def test_score_reports_a_pause_before_the_word_after_a_long_gap(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: canned())
    pauses = scoring.score("any.wav", PASSAGE)["pauses"]
    # red ends at frame 43 (0.86 s); kite starts at frame 200 (4.0 s)
    assert pauses == [{"before_word": 4, "seconds": 3.14}]


def test_short_gaps_are_not_pauses(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: fake([wa(0, 10, [0.9]), wa(60, 70, [0.9])]))  # 1.0 s gap -> a pause
    assert len(scoring.score("any.wav", "one two")["pauses"]) == 1
    monkeypatch.setattr(aligner, "align", lambda path, words: fake([wa(0, 10, [0.9]), wa(59, 70, [0.9])]))  # 0.98 s gap -> not
    assert scoring.score("any.wav", "one two")["pauses"] == []


def test_the_aligner_gets_normalised_words_only(monkeypatch):
    seen = {}

    def spy(path, words):
        seen["words"] = words
        return fake([wa(0, 5, [0.9]), wa(10, 15, [0.9]), wa(20, 25, [0.9])])

    monkeypatch.setattr(aligner, "align", spy)
    result = scoring.score("any.wav", "Mag-aral ka, Niño!")
    assert seen["words"] == ["magaral", "ka", "ninyo"]
    assert [w["text"] for w in result["words"]] == ["Mag-aral", "ka,", "Niño!"]


def test_words_with_no_letters_are_matched_and_skip_alignment(monkeypatch):
    seen = {}

    def spy(path, words):
        seen["words"] = words
        return fake([wa(0, 10, [0.9]), wa(100, 110, [0.9])])

    monkeypatch.setattr(aligner, "align", spy)
    result = scoring.score("any.wav", "Ben 2026 kite")
    assert seen["words"] == ["ben", "kite"]
    middle = result["words"][1]
    assert (middle["i"], middle["text"], middle["label"], middle["score"]) == (1, "2026", "matched", 1.0)
    assert middle["start"] == middle["end"] == 0.2  # sits at the previous word's end


def test_audio_too_short_for_the_text_means_everything_was_skipped(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: None)
    result = scoring.score("any.wav", "Ben 2026 kite")
    assert [w["label"] for w in result["words"]] == ["skipped", "matched", "skipped"]
    assert result["pauses"] == []


def test_empty_or_letterless_passages_never_touch_the_model(monkeypatch):
    def boom(*_):
        raise AssertionError("the aligner should not run")

    monkeypatch.setattr(aligner, "align", boom)
    empty = scoring.score("any.wav", "")
    assert (empty["words"], empty["pauses"]) == ([], [])
    only_digits = scoring.score("any.wav", "2026 —")
    assert [w["label"] for w in only_digits["words"]] == ["matched", "matched"]


def test_timings_split_alignment_from_labelling(monkeypatch):
    def slow_align(path, words):
        import time
        time.sleep(0.05)
        return canned()

    monkeypatch.setattr(aligner, "align", slow_align)
    timings = scoring.score("any.wav", PASSAGE)["timings"]
    assert set(timings) == {"align_ms", "score_ms"}
    assert timings["align_ms"] >= 50  # the aligner's time lands in align_ms...
    assert timings["score_ms"] < 50  # ...not in score_ms


def test_every_return_path_has_timings(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: None)  # too short
    assert set(scoring.score("any.wav", "Ben kite")["timings"]) == {"align_ms", "score_ms"}
    assert set(scoring.score("any.wav", "")["timings"]) == {"align_ms", "score_ms"}
    assert set(scoring.score("any.wav", "2026")["timings"]) == {"align_ms", "score_ms"}


# --- word_timings() with canned alignments (frame = 0.02 s) -----------------------

def test_words_that_touch_meet_at_the_midpoint(monkeypatch):
    # raw spans 0.20-0.32 and 0.38-0.50: a 0.06 s gap inside a sentence
    monkeypatch.setattr(aligner, "align", lambda path, words: fake([wa(10, 16, [0.9]), wa(19, 25, [0.9])]))
    first, second = scoring.word_timings("any.wav", "Ben has")
    assert first["end"] == second["start"] == 0.35


def test_a_sentence_break_keeps_its_silence_out_of_both_words(monkeypatch):
    # "kite." ends at 0.50, "He" starts at 2.00: each gets its pad, the silence between stays out
    monkeypatch.setattr(aligner, "align", lambda path, words: fake([wa(19, 25, [0.9]), wa(100, 104, [0.9])]))
    kite, he = scoring.word_timings("any.wav", "kite. He")
    assert kite["end"] == pytest.approx(0.50 + scoring.PAD_AFTER_SEC)
    assert he["start"] == pytest.approx(2.00 - scoring.PAD_BEFORE_SEC)


def test_first_and_last_words_are_padded_but_stay_inside_the_recording(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: fake([wa(2, 10, [0.9]), wa(100, 498, [0.9])], duration=10.0))
    first, last = scoring.word_timings("any.wav", "one two")
    assert first["start"] == 0.0  # 0.04 - 0.10 would be before the recording starts
    assert last["end"] == 10.0  # 9.96 + 0.15 would run past its end


def test_timings_keep_passage_indexing_and_skip_letterless_words(monkeypatch):
    seen = {}

    def spy(path, words):
        seen["words"] = words
        return fake([wa(10, 16, [0.9]), wa(100, 110, [0.9])])

    monkeypatch.setattr(aligner, "align", spy)
    timings = scoring.word_timings("any.wav", "Ben 2026 kite.")
    assert seen["words"] == ["ben", "kite"]
    assert [t["i"] for t in timings] == [0, 1, 2]
    assert [t["text"] for t in timings] == ["Ben", "2026", "kite."]
    assert timings[1]["start"] == timings[1]["end"] == timings[0]["end"]  # zero length, after "Ben"


def test_word_clips_never_overlap(monkeypatch):
    spans = [wa(5, 9, [0.9]), wa(9, 12, [0.9]), wa(12, 30, [0.9]), wa(31, 33, [0.9]), wa(200, 240, [0.9])]
    monkeypatch.setattr(aligner, "align", lambda path, words: fake(spans))
    timings = scoring.word_timings("any.wav", "a b c d e")
    assert all(t["start"] <= t["end"] for t in timings)
    assert all(a["end"] <= b["start"] for a, b in zip(timings, timings[1:]))


def test_word_timings_too_short_raises(monkeypatch):
    monkeypatch.setattr(aligner, "align", lambda path, words: None)
    with pytest.raises(ValueError, match="too short"):
        scoring.word_timings("any.wav", "Ben has a red kite")


def test_word_timings_without_letters_never_touches_the_model(monkeypatch):
    def boom(*_):
        raise AssertionError("the aligner should not run")

    monkeypatch.setattr(aligner, "align", boom)
    assert scoring.word_timings("any.wav", "") == []
    assert scoring.word_timings("any.wav", "2026 —") == [
        {"i": 0, "text": "2026", "start": 0.0, "end": 0.0}, {"i": 1, "text": "—", "start": 0.0, "end": 0.0}]
