"""GET /passages: the texts a child can read in a Basa check. Contract: docs/API.md."""

from fastapi import APIRouter, Depends

from app.routes.assessments import get_conn

router = APIRouter(prefix="/passages", tags=["passages"])


@router.get("")
def list_passages(conn=Depends(get_conn)) -> list[dict]:
    """Every passage, by id."""
    rows = conn.execute("SELECT id, title, language, grade, text FROM passages ORDER BY id").fetchall()
    return [dict(r) for r in rows]
