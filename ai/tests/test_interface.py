"""The ai interface returns the shapes in docs/API.md (P1-AI-1 skeleton)."""

import json
import struct
import wave
from pathlib import Path

import pytest

import ai

REPO = Path(__file__).resolve().parents[2]
EXAMPLE = json.loads((REPO / "docs" / "api" / "assess.example.json").read_text(encoding="utf-8"))
PASSAGES = json.loads((REPO / "data" / "passages" / "passages.json").read_text(encoding="utf-8"))
FIL = next(p for p in PASSAGES if p["id"] == "fil_g2_01")["text"]

LABELS = {"matched", "misread", "skipped"}


@pytest.fixture
def wav(tmp_path):
    """Two seconds of silence, 16 kHz mono."""
    path = tmp_path / "reading.wav"
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack("<h", 0) * 32000)
    return str(path)


def test_score_word_keys_match_the_contract(wav):
    result = ai.score(wav, FIL)
    expected_keys = set(EXAMPLE["words"][0])
    assert set(result) == {"words", "pauses"}
    assert all(set(w) == expected_keys for w in result["words"])


def test_score_returns_one_word_per_passage_word_in_order(wav):
    words = ai.score(wav, FIL)["words"]
    assert [w["i"] for w in words] == list(range(len(FIL.split())))
    assert [w["text"] for w in words] == FIL.split()


def test_score_values_are_in_range(wav):
    for w in ai.score(wav, FIL)["words"]:
        assert w["label"] in LABELS
        assert 0 <= w["score"] <= 1
        assert 0 <= w["start"] <= w["end"] <= 2.0 + 1e-6


def test_pauses_use_the_contract_keys(wav):
    pauses = ai.score(wav, FIL)["pauses"]
    assert isinstance(pauses, list)
    for p in pauses:
        assert set(p) == set(EXAMPLE["pauses"][0])


def test_word_timings_shape_and_order(wav):
    timings = ai.word_timings(wav, FIL)
    assert all(set(t) == {"i", "text", "start", "end"} for t in timings)
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(timings, timings[1:]))


def test_check_word_shape(wav):
    result = ai.check_word(wav, "palay")
    assert set(result) == {"result", "score"}
    assert result["result"] in {"match", "no_match"}
    assert 0 <= result["score"] <= 1


def test_empty_passage_gives_no_words(wav):
    assert ai.score(wav, "")["words"] == []
    assert ai.word_timings(wav, "   ") == []


def test_unreadable_audio_does_not_crash(tmp_path):
    missing = str(tmp_path / "nope.wav")
    assert len(ai.score(missing, FIL)["words"]) == len(FIL.split())
