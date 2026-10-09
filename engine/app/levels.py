"""Reading speed and reading level from a check's final word labels.

P1-BE2-1 needs a score that follows the teacher's overrides, so this module
exists now with words correct per minute (WCPM) only. The reading level stays
None (NULL in the database, null in the API) until P1-BE2-2 checks the level
names against DepEd's current CRLA profiles. P1-BE2-2 replaces compute_level
and may refine compute_wcpm; callers only use recompute.
"""

from collections.abc import Iterable


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


def compute_level(wcpm: int) -> str | None:
    """Placeholder until P1-BE2-2: no level is reported yet."""
    return None


def recompute(final_labels: Iterable[str], duration_sec: float) -> tuple[int, str | None]:
    """Return (wcpm, level) for a check, from its final (overridden) labels."""
    wcpm = compute_wcpm(final_labels, duration_sec)
    return wcpm, compute_level(wcpm)
