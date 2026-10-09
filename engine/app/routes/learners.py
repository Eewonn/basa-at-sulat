"""Learner endpoints: the class list, stats, Sanay practice sets (P2-BE2-1) and progress (P2-BE2-2). Contract: docs/API.md."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.class_view import _latest_checks
from app.practice import LearnerNotFoundError, build_practice_set
from app.progress import build_progress
from app.routes.assessments import get_conn
from app.stats import build_stats, local_day, reading_days, stars, streak

router = APIRouter(prefix="/learners", tags=["learners"])


@router.get("")
def list_learners(conn=Depends(get_conn)) -> list[dict]:
    """Every learner in the class, by id, with stars, streak and a summary of their latest confirmed check if they have one."""
    latest = {r["learner_id"]: r for r in _latest_checks(conn)}
    out = []
    for row in conn.execute("SELECT id, display_name, grade FROM learners ORDER BY id"):
        learner = dict(row)
        learner["stars"] = stars(conn, row["id"])
        learner["streak_days"] = streak(reading_days(conn, row["id"]), date.today())
        check = latest.get(row["id"])
        if check is not None and check["assessment_id"] is not None:
            learner.update(
                level=check["level"],
                latest_wcpm=None if check["wcpm"] is None else int(check["wcpm"]),
                last_check=local_day(check["confirmed_at"]).isoformat(),
                needs_practice=check["missed_count"] > 0,
            )
        out.append(learner)
    return out


@router.get("/{learner_id}/stats")
def get_stats(learner_id: str, conn=Depends(get_conn)) -> dict:
    """Stars, streak, reading time, WCPM over time and practice words, all counted from saved rows."""
    try:
        return build_stats(conn, learner_id)
    except LearnerNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from None


@router.get("/{learner_id}/practice")
def get_practice(learner_id: str, conn=Depends(get_conn)) -> dict:
    """The learner's missed words from their latest confirmed check, each with its sentence and clip."""
    try:
        return {"items": build_practice_set(conn, learner_id)}
    except LearnerNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from None


@router.get("/{learner_id}/progress")
def get_progress(learner_id: str, conn=Depends(get_conn)) -> dict:
    """The learner's latest two confirmed checks on the same passage, compared word by word."""
    try:
        return build_progress(conn, learner_id)
    except LearnerNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from None
