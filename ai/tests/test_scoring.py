"""score() labelling, timing and pauses, driven by canned alignments (no model needed)."""

import pytest

from ai import aligner, scoring
from ai.aligner import Alignment, WordAlignment


def fake(words, frame_sec=0.02, duration=10.0):
    return Alignment(words=words, frame_sec=frame_sec, duration_sec=duration)


def wa(start, end, scores):
    return WordAlignment(start_frame=start, end_frame=end, token_scores=scores)


# --- label_word -------------------------------------------------------------

@pytest.mark.parametrize(
    "mean_prob, n_chars, fpc, expected",
    [
        (0.95, 5, 3.0, "matched"),
        (0.6, 5, 3.0, "matched"),  # at the cutoff is still a match
        (0.59, 5, 3.0, "misread"),
        (0.2, 5, 3.0, "misread"),  # poor fit with a normal duration: said something else
        (0.0, 3, 1.0, "skipped"),  # poor fit and squeezed to one frame per letter
        (0.0, 1, 1.0, "misread"),  # a one-letter word is always 1 frame/letter: can't be "skipped"
        (0.55, 4, 1.0, "misread"),  # squeezed but not hopeless: not enough to call it skipped
    ],
)
def test_label_word(mean_prob, n_chars, fpc, expected):
    assert scoring.label_word(mean_prob, n_chars, fpc) == expected


# --- score() with canned alignments -----------------------------------------

PASSAGE = "Ben has a red kite"  # ben / has / a / red / kite


def canned():
    return fake([
        wa(10, 16, [0.9, 0.9, 0.9]),  # Ben: fits
        wa(20, 29, [0.2, 0.2, 0.2]),  # has: poor fit, normal length
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
    assert ben["score"] == 0.9 and ben["start"] == 0.2 and ben["end"] == 0.32


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
    assert scoring.score("any.wav", "") == {"words": [], "pauses": []}
    only_digits = scoring.score("any.wav", "2026 —")
    assert [w["label"] for w in only_digits["words"]] == ["matched", "matched"]
