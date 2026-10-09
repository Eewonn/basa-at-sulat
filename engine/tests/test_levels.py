"""Tests for reading speed and level (P1-BE2-1's recompute boundary)."""

import pytest

from app.levels import compute_level, compute_wcpm, recompute


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


def test_level_is_empty_until_p1_be2_2():
    assert compute_level(80) is None


def test_recompute_returns_wcpm_and_level():
    assert recompute(["matched", "misread"], 60) == (1, None)
