"""Class view endpoints (P2-BE2-3). Contract: docs/API.md."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.class_view import build_class, export_csv
from app.routes.assessments import get_conn

router = APIRouter(prefix="/class", tags=["class"])

EXPORT_FILE_NAME = "basa-results.csv"


# Plain `def`, not `async def`: FastAPI runs it in a worker thread, so a slow
# Ollama call for an uncached plan doesn't hold up other requests.
@router.get("")
def get_class(refresh: bool = False, conn=Depends(get_conn)) -> dict:
    """Learners grouped by reading level, each group with its common missed words and a draft plan.

    `?refresh=1` makes new plans instead of using cached ones (slow: it always runs Ollama).
    """
    return build_class(conn, refresh=refresh)


@router.get("/export.csv")
def get_export(conn=Depends(get_conn)) -> Response:
    """One row per learner from their latest confirmed check, as a CSV download."""
    return Response(
        content=export_csv(conn).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{EXPORT_FILE_NAME}"'},
    )
