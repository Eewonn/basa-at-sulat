"""The ai interface returns the shapes in docs/API.md.

score() runs on the real MMS model here (skipped if the weights aren't downloaded); the audio is silence,
so these check shape and robustness, not accuracy. Accuracy is measured by eval/ on real recordings.
"""

import json
from pathlib import Path

import pytest

import ai
from conftest import requires_model

REPO = Path(__file__).resolve().parents[2]
EXAMPLE = json.loads((REPO / "docs" / "api" / "assess.example.json").read_text(encoding="utf-8"))
PASSAGES = json.loads((REPO / "data" / "passages" / "passages.json").read_text(encoding="utf-8"))
FIL = next(p for p in PASSAGES if p["id"] == "fil_g2_01")["text"]
LABELS = {"matched", "misread", "skipped"}


def check_contract(result, text, duration):
    expected_keys = set(EXAMPLE["words"][0])
    assert set(result) == {"words", "pauses", "timings"}
    assert set(result["timings"]) == {"align_ms", "score_ms"}
    assert all(isinstance(v, int) and v >= 0 for v in result["timings"].values())
    words = result["words"]
    assert [w["i"] for w in words] == list(range(len(text.split())))
    assert [w["text"] for w in words] == text.split()
    for w in words:
        assert set(w) == expected_keys
        assert w["label"] in LABELS
        assert 0 <= w["score"] <= 1
        assert 0 <= w["start"] <= w["end"] <= duration + 0.1
    for p in result["pauses"]:
        assert set(p) == set(EXAMPLE["pauses"][0])


@requires_model
def test_score_shape_when_the_audio_is_too_short_for_the_text(make_wav):
    result = ai.score(make_wav(2), FIL)  # ~100 frames for ~110 letters
    check_contract(result, FIL, 2)
    assert {w["label"] for w in result["words"]} == {"skipped"}


@requires_model
def test_score_shape_on_a_full_alignment(make_wav):
    check_contract(ai.score(make_wav(30), FIL), FIL, 30)


@requires_model
def test_score_raises_on_an_unreadable_file(tmp_path):
    with pytest.raises(Exception):
        ai.score(str(tmp_path / "missing.wav"), FIL)


@requires_model
def test_word_timings_shape_on_a_full_alignment(make_wav):
    timings = ai.word_timings(make_wav(30), FIL)
    assert all(set(t) == {"i", "text", "start", "end"} for t in timings)
    assert [t["i"] for t in timings] == list(range(len(FIL.split())))
    assert [t["text"] for t in timings] == FIL.split()
    assert all(0 <= t["start"] <= t["end"] <= 30.1 for t in timings)
    assert all(a["end"] <= b["start"] for a, b in zip(timings, timings[1:]))


@requires_model
def test_word_timings_rejects_audio_too_short_for_the_text(make_wav):
    with pytest.raises(ValueError):
        ai.word_timings(make_wav(2), FIL)


def test_word_timings_of_nothing_is_empty(make_wav):
    assert ai.word_timings(make_wav(2), "   ") == []


def test_check_word_stub_shape(make_wav):
    result = ai.check_word(make_wav(2), "palay")
    assert set(result) == {"result", "score"}
    assert result["result"] in {"match", "no_match"}
    assert 0 <= result["score"] <= 1


@requires_model
def test_warm_up_loads_the_model_once():
    from ai import aligner

    aligner._load.cache_clear()
    assert not ai.model_loaded()
    ai.warm_up()
    assert ai.model_loaded()
    ai.warm_up()  # second call is free: same cached model
    assert aligner._load.cache_info().misses == 1
