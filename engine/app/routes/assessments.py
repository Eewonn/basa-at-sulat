"""Assessment endpoints (P1-BE2-1). Contract: docs/API.md."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from app.assessments import (
    AssessmentConfirmedError,
    AssessmentNotFoundError,
    override_word,
)
from app.db import connect, get_db_path

router = APIRouter(prefix="/assessments", tags=["assessments"])


class WordOverride(BaseModel):
    """PATCH body. Anything other than the three labels is rejected with 422."""

    label: Literal["matched", "misread", "skipped"]


def get_conn() -> Iterator[sqlite3.Connection]:
    """One connection per request, always closed (an open one locks the file on Windows)."""
    db_path = get_db_path()
    # connect() would silently create an empty file here, and every query
    # would then fail with "no such table".
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"no database at {db_path}. Run `python -m app.seed` from engine/ first.",
        )
    with closing(connect(db_path)) as conn:
        yield conn


@router.patch("/{assessment_id}/words/{i}")
def patch_word(
    body: WordOverride,
    assessment_id: str,
    i: int = Path(ge=0),
    conn=Depends(get_conn),
) -> dict:
    """Apply the teacher's override and return the recomputed assessment."""
    try:
        return override_word(conn, assessment_id, i, body.label)
    except AssessmentNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from None
    except AssessmentConfirmedError as err:
        raise HTTPException(status_code=409, detail=str(err)) from None
