import logging

from fastapi import FastAPI

from app.assess import router as assess_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

app = FastAPI(title="Basa at Sulat engine")
app.include_router(assess_router)


@app.get("/health")
def health():
    return {"ok": True, "models": {"aligner": "not_loaded", "ollama": "unknown"}}
