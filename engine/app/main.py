import json
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

FIXTURE = Path(__file__).resolve().parents[2] / "docs" / "api" / "assess.example.json"

app = FastAPI(title="Basa at Sulat engine")


@app.get("/health")
def health():
    return {"ok": True, "models": {"aligner": "not_loaded", "ollama": "unknown"}}


@app.post("/assess")
def assess(
    audio: UploadFile = File(...),
    passage_id: str = Form(...),
    learner_id: str = Form(...),
):
    # Phase 0 stub: contract shape only. Real scoring arrives in P1-BE1-1.
    return json.loads(FIXTURE.read_text(encoding="utf-8"))
