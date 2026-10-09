"""Learner endpoints: Sanay practice sets (P2-BE2-1) and progress (P2-BE2-2). Contract: docs/API.md."""

from fastapi import APIRouter, Depends, HTTPException

from app.practice import LearnerNotFoundError, build_practice_set
from app.progress import build_progress
from app.routes.assessments import get_conn

router = APIRouter(prefix="/learners", tags=["learners"])


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
