"""A learner's reading record for the profile (GET /learners/{id}/stats). Contract: docs/API.md.

Everything is counted from saved rows: confirmed checks and Sanay attempts. Nothing is estimated.
Days are counted in this laptop's time zone, because the engine and the app run on the same laptop
and a check at 7 am in Manila is still the previous day in UTC.
"""

import sqlite3
from datetime import date, datetime, timedelta

from app.practice import LearnerNotFoundError, build_practice_set


def _local_day(timestamp: str) -> date:
    """The local calendar day of a stored UTC timestamp such as 2026-10-05T01:10:00.000Z."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().date()


def streak(days: set[date], today: date) -> int:
    """Consecutive days read up to today. A streak isn't broken until a whole day is missed,
    so one that ended yesterday still counts."""
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


def reading_days(conn: sqlite3.Connection, learner_id: str) -> set[date]:
    """Days with a confirmed check or a Sanay attempt."""
    rows = conn.execute(
        "SELECT confirmed_at AS at FROM assessments WHERE learner_id = ? AND status = 'confirmed' "
        "UNION ALL SELECT created_at FROM practice_attempts WHERE learner_id = ?",
        (learner_id, learner_id),
    ).fetchall()
    return {_local_day(r["at"]) for r in rows}


def stars(conn: sqlite3.Connection, learner_id: str) -> int:
    """Words the learner said right in Sanay."""
    return conn.execute(
        "SELECT COUNT(*) FROM practice_attempts WHERE learner_id = ? AND result = 'match'", (learner_id,)
    ).fetchone()[0]


def build_stats(conn: sqlite3.Connection, learner_id: str, today: date | None = None) -> dict:
    practicing = [item["word"] for item in build_practice_set(conn, learner_id)]  # raises for an unknown learner
    checks = conn.execute(
        "SELECT confirmed_at, wcpm, duration_sec FROM assessments "
        "WHERE learner_id = ? AND status = 'confirmed' ORDER BY confirmed_at, created_at, id",
        (learner_id,),
    ).fetchall()
    days = reading_days(conn, learner_id)
    return {
        "stars": stars(conn, learner_id),
        "streak_days": streak(days, today or date.today()),
        # Recording time of confirmed checks; Sanay attempts don't store their length.
        "minutes_read": round(sum(c["duration_sec"] for c in checks) / 60),
        "wcpm_history": [
            {"date": _local_day(c["confirmed_at"]).isoformat(), "wcpm": int(c["wcpm"])}
            for c in checks if c["wcpm"] is not None
        ],
        "practicing": practicing,
        "days_read": sorted(d.isoformat() for d in days),
    }


__all__ = ["LearnerNotFoundError", "build_stats", "reading_days", "stars", "streak"]
