"""Tests for the Sulat story draft (POST /books/draft). Ollama is never called."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.plans import PlanError
from app.story import build_story_prompt, check_story

client = TestClient(app)
STORY = {"title": "Ang Aso", "text": "May aso si Ana. Puti ito. Naglalaro sila sa bakuran."}


def fake_replies(monkeypatch, *responses):
    calls = []

    def post(prompt, settings, seed, options=None, format=None):
        calls.append({"seed": seed, "format": format})
        response = responses[len(calls) - 1]
        if isinstance(response, Exception):
            raise response
        return {"response": response}

    monkeypatch.setattr("app.story._post_generate", post)
    return calls


def test_draft_returns_title_and_text(monkeypatch):
    calls = fake_replies(monkeypatch, json.dumps(STORY))
    r = client.post("/books/draft", json={"topic": "hayop", "language": "fil"})
    assert r.status_code == 200
    assert r.json() == STORY
    assert calls[0]["format"] == "json"


def test_a_bad_reply_is_retried_once_with_another_seed(monkeypatch):
    calls = fake_replies(monkeypatch, "not json", json.dumps(STORY))
    assert client.post("/books/draft", json={"topic": "hayop", "language": "fil"}).json() == STORY
    assert calls[0]["seed"] != calls[1]["seed"]


def test_two_bad_replies_are_503(monkeypatch):
    fake_replies(monkeypatch, "{}", json.dumps({**STORY, "text": "May 2 aso."}))
    r = client.post("/books/draft", json={"topic": "hayop", "language": "fil"})
    assert r.status_code == 503
    assert "digits" in r.json()["detail"]


def test_ollama_down_is_503(monkeypatch):
    fake_replies(monkeypatch, PlanError("could not reach Ollama"))
    r = client.post("/books/draft", json={"topic": "hayop", "language": "fil"})
    assert r.status_code == 503


@pytest.mark.parametrize("body", [
    {"topic": "dagat", "language": "fil"},
    {"topic": "hayop", "language": "ilo"},
    {"language": "fil"},
])
def test_bad_input_is_422(monkeypatch, body):
    fake_replies(monkeypatch)
    assert client.post("/books/draft", json=body).status_code == 422


def test_the_idea_goes_into_the_prompt():
    assert "Ideya ng guro: isang pusa sa bubong" in build_story_prompt("hayop", "fil", " isang pusa\nsa bubong ")
    assert "Ideya ng guro" not in build_story_prompt("hayop", "fil")
    assert "Topic: animals" in build_story_prompt("hayop", "eng")


def test_check_story_rejects_long_stories():
    with pytest.raises(PlanError, match="over"):
        check_story(json.dumps({"title": "T", "text": "salita " * 81}))
