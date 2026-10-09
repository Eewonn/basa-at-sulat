"""Class view: learners grouped by reading level, with a draft plan per group (P2-BE2-3).

Contract: docs/API.md, `GET /class` and `GET /class/export.csv`.

- Each learner goes in the group for the level of their latest confirmed
  check (same order as practice and progress). Learners with no confirmed
  check are left out of the groups but still get a row in the export.
- A group's common missed words are the words at least MIN_LEARNERS_PER_WORD
  of its learners missed (final label misread or skipped), most-missed first,
  capped at MAX_COMMON_WORDS. With only one Filipino check in the group, that
  child's own missed words are used, so a lone low reader still gets word
  practice instead of a fluency activity.
- Plans are Filipino only. Only checks on Filipino passages count towards the
  missed words, and a group with no Filipino check gets no plan (null), so the
  model is never asked for English or another language.
"""

import csv
import io
import logging
import sqlite3
from collections import Counter

from ai.text import normalize_word
from app.levels import LEVELS
from app.plan_cache import get_plan
from app.plans import PUNCTUATION, SUPPORTED_LANGUAGES, GroupStats, PlanError
from app.practice import MISSED_LABELS

logger = logging.getLogger(__name__)

# A word one child missed is that child's practice, not a group activity
# (unless the child is the only one with a Filipino check in the group).
MIN_LEARNERS_PER_WORD = 2
# Few enough for a 10-minute small-group activity.
MAX_COMMON_WORDS = 5

EXPORT_COLUMNS = (
    "learner_id", "display_name", "latest_check_date", "passage_title",
    "wcpm", "level", "missed_count",
)
# Excel runs a cell starting with these as a formula (CSV injection).
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def _latest_checks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every learner, with their latest confirmed check's fields, or NULLs if they have none."""
    # Same tie-breaks as app/practice.py, so "latest" means the same check on every screen.
    return conn.execute(
        """
        WITH ranked AS (
            SELECT a.*, ROW_NUMBER() OVER (
                PARTITION BY a.learner_id
                ORDER BY a.confirmed_at DESC, a.created_at DESC, a.id DESC
            ) AS rn
            FROM assessments a WHERE a.status = 'confirmed'
        )
        SELECT l.id AS learner_id, l.display_name,
               r.id AS assessment_id, r.confirmed_at, r.wcpm, r.level,
               p.title AS passage_title, p.language,
               (SELECT COUNT(*) FROM word_results w
                 WHERE w.assessment_id = r.id AND w.final_label IN (?, ?)) AS missed_count
        FROM learners l
        LEFT JOIN ranked r ON r.learner_id = l.id AND r.rn = 1
        LEFT JOIN passages p ON p.id = r.passage_id
        ORDER BY l.id
        """,
        MISSED_LABELS,
    ).fetchall()


def _missed_words(conn: sqlite3.Connection, assessment_id: str) -> dict[str, tuple[int, str]]:
    """Map each missed word's key to (first index, word as written without punctuation), once per word."""
    rows = conn.execute(
        "SELECT i, text FROM word_results WHERE assessment_id = ? AND final_label IN (?, ?) "
        "ORDER BY i",
        (assessment_id, *MISSED_LABELS),
    )
    words: dict[str, tuple[int, str]] = {}
    for row in rows:
        word = row["text"].strip(PUNCTUATION)
        if not word:
            continue  # a stray dash or quote mark isn't a word to teach
        # Same matching rule as practice, so "Palay," and "palay" are one word.
        key = normalize_word(word) or word.casefold()
        words.setdefault(key, (row["i"], word))
    return words


def common_missed_words(conn: sqlite3.Connection, assessment_ids: list[str]) -> list[str]:
    """Words missed by at least MIN_LEARNERS_PER_WORD of these checks, most-missed first.

    With a single check, its own missed words count, in passage order.

    Ties go to the word that comes earliest in its passage, then to the key,
    so the list (and the cached plan) is stable between loads. Each word is
    shown in the spelling most of the checks had (e.g. "palay" over "Palay"
    at the start of a sentence), ties going to the first check.
    """
    learners_missed: Counter[str] = Counter()
    first_index: dict[str, int] = {}
    spellings: dict[str, Counter[str]] = {}
    for assessment_id in assessment_ids:
        for key, (i, word) in _missed_words(conn, assessment_id).items():
            learners_missed[key] += 1
            first_index[key] = min(i, first_index.get(key, i))
            spellings.setdefault(key, Counter())[word] += 1

    needed = min(MIN_LEARNERS_PER_WORD, len(assessment_ids))
    common = [key for key, count in learners_missed.items() if count >= needed]
    common.sort(key=lambda key: (-learners_missed[key], first_index[key], key))
    # most_common keeps insertion order on ties, which is check order here.
    return [spellings[key].most_common(1)[0][0] for key in common[:MAX_COMMON_WORDS]]


def _level_order(level: str) -> tuple[int, str]:
    """Lowest CRLA level first; any unknown name after them, alphabetically."""
    return (LEVELS.index(level), "") if level in LEVELS else (len(LEVELS), level)


def _draft_plan(group: GroupStats, refresh: bool) -> str | None:
    try:
        return get_plan(group, refresh=refresh)
    except PlanError as err:
        # A broken template shouldn't take down the whole class view.
        logger.error("no draft plan for level '%s': %s", group.level, err)
        return None


def build_class(conn: sqlite3.Connection, refresh: bool = False) -> dict:
    """Group learners by the level of their latest confirmed check, each group with a draft plan.

    refresh=True skips cached plans and makes new ones (see plan_cache.get_plan).
    """
    by_level: dict[str, list[sqlite3.Row]] = {}
    for row in _latest_checks(conn):
        if row["assessment_id"] is None:
            continue  # never checked: no level to group by
        if row["level"] is None:
            # levels.py fills it on every save, so this means a hand-edited row.
            logger.warning("learner %s left out of the class view: check %s has no level",
                           row["learner_id"], row["assessment_id"])
            continue
        by_level.setdefault(row["level"], []).append(row)

    groups = []
    for level in sorted(by_level, key=_level_order):
        rows = by_level[level]
        # Plans are Filipino only (docs/DECISIONS.md); English is deferred.
        plan_checks = [row["assessment_id"] for row in rows
                       if row["language"] in SUPPORTED_LANGUAGES]
        words = common_missed_words(conn, plan_checks)
        plan = None
        if plan_checks:
            plan = _draft_plan(GroupStats(level=level, learner_count=len(rows),
                                          common_missed_words=words, language="fil"),
                               refresh)
        groups.append({
            "level": level,
            "learner_ids": [row["learner_id"] for row in rows],
            "common_missed_words": words,
            "draft_plan": plan,
        })
    return {"groups": groups}


def _safe_cell(value):
    """Stop Excel from running a text cell as a formula. Numbers and blanks pass as they are."""
    if isinstance(value, str) and value.startswith(FORMULA_STARTS):
        return "'" + value
    return value


def export_rows(conn: sqlite3.Connection) -> list[dict]:
    """One row per learner, from their latest confirmed check. Blank check columns if there is none."""
    rows = []
    for row in _latest_checks(conn):
        checked = row["assessment_id"] is not None
        rows.append({
            "learner_id": row["learner_id"],
            "display_name": row["display_name"],
            # confirmed_at is ISO 8601 UTC, so the first 10 characters are the date.
            "latest_check_date": row["confirmed_at"][:10] if checked else None,
            "passage_title": row["passage_title"],
            "wcpm": row["wcpm"],
            "level": row["level"],
            "missed_count": row["missed_count"] if checked else None,
        })
    return rows


def export_csv(conn: sqlite3.Connection) -> str:
    """The export as CSV text, with a BOM so Excel reads ñ and accents as UTF-8."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=EXPORT_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for row in export_rows(conn):
        writer.writerow({column: _safe_cell(value) for column, value in row.items()})
    return "﻿" + out.getvalue()
