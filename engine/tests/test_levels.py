"""Tests for reading speed (P1-BE2-1) and the estimated CRLA level (P1-BE2-2)."""

import pytest

from app.levels import (
    AT_GRADE_LEVEL,
    DEVELOPING,
    HIGH_EMERGING,
    LEVELS,
    LOW_EMERGING,
    TRANSITIONING,
    compute_level,
    compute_wcpm,
    recompute,
)


def test_wcpm_counts_only_matched_words():
    labels = ["matched", "matched", "misread", "skipped", "matched"]
    # 3 correct words in 30 seconds is 6 per minute.
    assert compute_wcpm(labels, 30) == 6


def test_wcpm_rounds_to_whole_number():
    # 5 correct in 41.2 s is 7.28 per minute.
    assert compute_wcpm(["matched"] * 5, 41.2) == 7


def test_wcpm_with_no_correct_words_is_zero():
    assert compute_wcpm(["misread", "skipped"], 20) == 0
    assert compute_wcpm([], 20) == 0


def test_wcpm_accepts_any_iterable():
    assert compute_wcpm((label for label in ["matched"] * 2), 60) == 2


@pytest.mark.parametrize("duration", [0, -5])
def test_wcpm_rejects_non_positive_duration(duration):
    with pytest.raises(ValueError, match="duration_sec"):
        compute_wcpm(["matched"], duration)


# --- Level (P1-BE2-2) ------------------------------------------------------
# A 20-word passage keeps the percentages easy: 1 word is 5%.

@pytest.mark.parametrize(
    ("correct", "wcpm", "level"),
    [
        (0, 0, LOW_EMERGING),
        (1, 60, HIGH_EMERGING),      # 5%
        (9, 60, HIGH_EMERGING),      # 45%, just under 50
        (10, 60, DEVELOPING),        # exactly 50
        (15, 60, DEVELOPING),        # 75%, just under 80
        (16, 60, TRANSITIONING),     # exactly 80
        (18, 60, TRANSITIONING),     # 90%, just under 95
        (19, 40, AT_GRADE_LEVEL),    # exactly 95% and exactly 40 wcpm
        (20, 100, AT_GRADE_LEVEL),
    ],
)
def test_level_boundaries(correct, wcpm, level):
    assert compute_level(correct, 20, wcpm) == level


def test_accurate_but_slow_reading_is_transitioning():
    assert compute_level(20, 20, 39) == TRANSITIONING


def test_speed_alone_never_lifts_an_inaccurate_reading():
    assert compute_level(15, 20, 200) == DEVELOPING


@pytest.mark.parametrize(("correct", "count"), [(19, 20), (38, 40), (57, 60)])
def test_exactly_95_percent_is_at_grade_level_for_any_passage_length(correct, count):
    assert compute_level(correct, count, 40) == AT_GRADE_LEVEL
    assert compute_level(correct - 1, count, 40) == TRANSITIONING


def test_levels_are_the_crla_names_lowest_first():
    assert LEVELS == (
        "Low Emerging", "High Emerging", "Developing", "Transitioning", "At Grade Level"
    )


@pytest.mark.parametrize("count", [0, -1])
def test_level_rejects_non_positive_passage_length(count):
    with pytest.raises(ValueError, match="passage_word_count"):
        compute_level(0, count, 0)


@pytest.mark.parametrize("correct", [-1, 21])
def test_level_rejects_correct_outside_the_passage(correct):
    with pytest.raises(ValueError, match="correct"):
        compute_level(correct, 20, 60)


# --- recompute -------------------------------------------------------------

def test_recompute_returns_wcpm_and_level():
    # 1 of a 2-word passage in 60 s: 50% accurate, 1 wcpm.
    assert recompute(["matched", "misread"], 60, 2) == (1, DEVELOPING)


def test_recompute_measures_accuracy_against_the_whole_passage():
    # The scorer returned 5 words, all matched, but the passage has 20:
    # 25% accurate, not 100%.
    assert recompute(["matched"] * 5, 10, 20) == (30, HIGH_EMERGING)


def test_recompute_accepts_a_generator():
    labels = (label for label in ["matched"] * 20)
    assert recompute(labels, 20, 20) == (60, AT_GRADE_LEVEL)
