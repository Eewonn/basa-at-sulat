"""Reading speed and reading level from a check's final word labels.

Both are computed from final (overridden) labels, so they follow the teacher.

The level uses DepEd's five CRLA reading-level names, but it is an ESTIMATE
from fluency alone. CRLA places a child using how much of the passage they
read accurately in a time limit AND how many comprehension questions they
answer; this app asks no comprehension questions. See docs/DECISIONS.md
(P1-BE2-2) for the sources and which cutoffs are ours.
"""

from collections.abc import Iterable

# Names exactly as on DepEd's CRLA submission form (SY 2026-27), lowest first.
LOW_EMERGING = "Low Emerging"
HIGH_EMERGING = "High Emerging"
DEVELOPING = "Developing"
TRANSITIONING = "Transitioning"
AT_GRADE_LEVEL = "At Grade Level"
LEVELS = (LOW_EMERGING, HIGH_EMERGING, DEVELOPING, TRANSITIONING, AT_GRADE_LEVEL)

# Accuracy cutoffs, as whole percents of the passage's words read correctly.
# 50 comes from CRLA's "less than 50% of the passage" band. 80 and 95 are our
# own picks and are pending review by a teacher on the team.
DEVELOPING_MIN_PCT = 50
TRANSITIONING_MIN_PCT = 80
AT_GRADE_LEVEL_MIN_PCT = 95

# CRLA's passages and time limits imply 40-50 words per minute to finish in
# time (Grade 3: 120 words in 3 minutes). 40 is the slowest of those rates.
AT_GRADE_LEVEL_MIN_WCPM = 40


def compute_wcpm(final_labels: Iterable[str], duration_sec: float) -> int:
    """Words read correctly per minute, rounded to a whole number.

    Only `matched` counts as correct: a misread or skipped word is an error
    until the teacher overrides it. Uses the whole recording's duration.
    """
    if duration_sec <= 0:
        # The schema forbids this too, but a zero would divide by zero first.
        raise ValueError(f"duration_sec must be greater than 0, got {duration_sec}")
    correct = sum(1 for label in final_labels if label == "matched")
    return round(correct * 60 / duration_sec)


def compute_level(correct: int, passage_word_count: int, wcpm: int) -> str:
    """Estimate the CRLA reading level from accuracy and speed.

    Accuracy is measured against the whole passage, not the words the scorer
    returned: a partial word list must not make a reading look more accurate.
    """
    if passage_word_count <= 0:
        raise ValueError(f"passage_word_count must be greater than 0, got {passage_word_count}")
    if not 0 <= correct <= passage_word_count:
        raise ValueError(
            f"correct must be between 0 and {passage_word_count}, got {correct}"
        )

    # Compare in whole numbers so an exact boundary (19 of 20 = 95%) can never
    # depend on floating-point rounding.
    def at_least(pct: int) -> bool:
        return correct * 100 >= pct * passage_word_count

    if correct == 0:
        return LOW_EMERGING  # CRLA: cannot read a single word accurately
    if not at_least(DEVELOPING_MIN_PCT):
        return HIGH_EMERGING
    if not at_least(TRANSITIONING_MIN_PCT):
        return DEVELOPING
    if at_least(AT_GRADE_LEVEL_MIN_PCT) and wcpm >= AT_GRADE_LEVEL_MIN_WCPM:
        return AT_GRADE_LEVEL
    # Accurate but slow, or 80-94% accurate.
    return TRANSITIONING


def recompute(final_labels: Iterable[str], duration_sec: float,
              passage_word_count: int) -> tuple[int, str]:
    """Return (wcpm, level) for a check, from its final (overridden) labels."""
    labels = list(final_labels)  # read twice below, and callers may pass a generator
    wcpm = compute_wcpm(labels, duration_sec)
    correct = sum(1 for label in labels if label == "matched")
    return wcpm, compute_level(correct, passage_word_count, wcpm)
