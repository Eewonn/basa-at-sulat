import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.assess import router as assess_router
from app.books import router as books_router
from app.retention import delete_owed_audio
from app.routes.assessments import router as assessments_router
from app.routes.learners import router as learners_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    delete_owed_audio()
    # Opt-in: loading the model takes ~10 s and needs torch plus the weights.
    if os.environ.get("BASA_WARM_UP") == "1":
        try:
            from ai import aligner

            aligner.warm_up()
            log.info("aligner warmed up")
        except Exception:
            log.exception("warm-up failed; the engine will keep running without the aligner")
    yield


app = FastAPI(title="Basa at Sulat engine", lifespan=lifespan)

# The desktop app's dev server (http://localhost:<port>) calls the engine from another origin, which a
# browser blocks unless the engine says it may. Only pages on this laptop are allowed, never a website;
# a packaged app loaded from file:// doesn't need this. The pattern must match the whole origin.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["content-type"],
)
app.include_router(assess_router)
app.include_router(books_router)
app.include_router(assessments_router)
app.include_router(learners_router)


def aligner_status() -> str:
    from ai import aligner

    return "loaded" if aligner.model_loaded() else "not_loaded"


@app.get("/health")
def health():
    return {"ok": True, "models": {"aligner": aligner_status(), "ollama": "unknown"}}
