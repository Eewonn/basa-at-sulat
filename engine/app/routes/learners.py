"""Learner endpoints: the class list, Sanay practice sets (P2-BE2-1) and progress (P2-BE2-2). Contract: docs/API.md."""

from fastapi import APIRouter, Depends, HTTPException

from app.class_view import _latest_checks
from app.practice import LearnerNotFoundError, build_practice_set
from app.progress import build_progress
from app.routes.assessments import get_conn

router = APIRouter(prefix="/learners", tags=["learners"])


@router.get("")
def list_learners(conn=Depends(get_conn)) -> list[dict]:
    """Every learner in the class, by id, with a summary of their latest confirmed check if they have one."""
    latest = {r["learner_id"]: r for r in _latest_checks(conn)}
    out = []
    for row in conn.execute("SELECT id, display_name, grade FROM learners ORDER BY id"):
        learner = dict(row)
        check = latest.get(row["id"])
        if check is not None and check["assessment_id"] is not None:
            learner.update(
                level=check["level"],
                latest_wcpm=None if check["wcpm"] is None else int(check["wcpm"]),
                last_check=check["confirmed_at"][:10],  # ISO 8601 UTC, so this is the date
                needs_practice=check["missed_count"] > 0,
            )
        out.append(learner)
    return out


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
