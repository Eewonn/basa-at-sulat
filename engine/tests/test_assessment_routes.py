"""Tests for PATCH /assessments/{id}/words/{i} (P1-BE2-1)."""

import copy
import json
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.assessments import confirm_assessment, save_assessment
from app.db import connect
from app.main import app
from app.seed import seed_db

# The frontend's mock result (docs/api/assess.example.json).
FIXTURE = Path(__file__).resolve().parents[2] / "docs" / "api" / "assess.example.json"
EXAMPLE = json.loads(FIXTURE.read_text(encoding="utf-8"))
client = TestClient(app)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """A seeded temp database holding the example as a draft, used by the API."""
    path = tmp_path / "test.db"
    seed_db(path)
    with closing(connect(path)) as conn:
        save_assessment(conn, copy.deepcopy(EXAMPLE))
    monkeypatch.setenv("BASA_DB_PATH", str(path))
    return path


def test_override_returns_recomputed_assessment(db_path):
    r = client.patch("/assessments/a_123/words/3", json={"label": "matched"})
    assert r.status_code == 200
    body = r.json()
    assert body["words"][3]["label"] == "matched"
    assert (body["wcpm"], body["level"], body["status"]) == (9, None, "draft")


def test_override_is_stored(db_path):
    client.patch("/assessments/a_123/words/4", json={"label": "matched"})
    with closing(connect(db_path)) as conn:
        row = conn.execute(
            "SELECT final_label FROM word_results WHERE assessment_id = 'a_123' AND i = 4"
        ).fetchone()
    assert row[0] == "matched"


def test_unknown_assessment_is_404(db_path):
    r = client.patch("/assessments/a_404/words/3", json={"label": "matched"})
    assert r.status_code == 404
    assert "a_404" in r.json()["detail"]


def test_unknown_word_is_404(db_path):
    r = client.patch("/assessments/a_123/words/7", json={"label": "matched"})
    assert r.status_code == 404


def test_confirmed_assessment_is_409(db_path):
    with closing(connect(db_path)) as conn:
        confirm_assessment(conn, "a_123")
    r = client.patch("/assessments/a_123/words/3", json={"label": "matched"})
    assert r.status_code == 409


@pytest.mark.parametrize("body", [{"label": "correct"}, {"label": None}, {}, {"text": "x"}])
def test_bad_body_is_422(db_path, body):
    r = client.patch("/assessments/a_123/words/3", json=body)
    assert r.status_code == 422


@pytest.mark.parametrize("i", ["-1", "abc"])
def test_bad_word_index_is_422(db_path, i):
    r = client.patch(f"/assessments/a_123/words/{i}", json={"label": "matched"})
    assert r.status_code == 422


def test_missing_database_is_503_and_not_created(tmp_path, monkeypatch):
    missing = tmp_path / "missing.db"
    monkeypatch.setenv("BASA_DB_PATH", str(missing))
    r = client.patch("/assessments/a_123/words/3", json={"label": "matched"})
    assert r.status_code == 503
    assert "python -m app.seed" in r.json()["detail"]
    assert not missing.exists()
