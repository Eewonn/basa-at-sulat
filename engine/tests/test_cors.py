"""Browser access: only pages on this laptop (localhost / 127.0.0.1, any port) may call the engine.

A browser enforces this, not Python, so the tests send the headers a browser would send."""

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app

client = TestClient(app)

ALLOWED = ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://localhost:80"]
REFUSED = [
    "http://localhost.evil.com",
    "http://localhost.evil.com:5173",
    "http://127.0.0.1.evil.com:5173",
    "https://localhost:5173",
    "https://example.com",
    "http://evil.com:5173",
    "http://localhost",  # no port: the pattern asks for one
    "null",
]


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    init_db(tmp_path / "test.db")


@pytest.mark.parametrize("origin", ALLOWED)
def test_a_page_on_this_laptop_gets_the_cors_header(origin):
    r = client.get("/health", headers={"Origin": origin})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", REFUSED)
def test_any_other_origin_gets_no_cors_header(origin):
    r = client.get("/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in r.headers


@pytest.mark.parametrize("method", ["PATCH", "POST", "GET"])
def test_the_preflight_a_browser_sends_first_is_accepted_for_a_local_page(method):
    r = client.options(
        "/assessments/a_1/words/0",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5174"
    assert method in r.headers["access-control-allow-methods"]
    assert "content-type" in r.headers["access-control-allow-headers"].lower()


def test_the_preflight_from_another_origin_is_refused():
    r = client.options(
        "/assessments/a_1/words/0",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "PATCH"},
    )
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_a_request_without_an_origin_is_untouched():
    r = client.get("/health")
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


def test_a_local_page_can_read_an_error_response_too():
    # The app shows "database missing" etc. from error bodies, so errors need the header as well.
    r = client.get("/books/b_nope", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 404
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
