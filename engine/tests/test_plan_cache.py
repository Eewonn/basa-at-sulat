"""Tests for cached group plans (P2-BE2-3): app/plan_cache.py and the Ollama health check."""

import json
import threading
import time
import urllib.error

import pytest

from app import plan_cache, plans
from app.plans import GroupStats, PlanError, PlanResult, ollama_status

GROUP = GroupStats(level="Developing", learner_count=3, common_missed_words=["palay", "bukid"])


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path))
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    return tmp_path


@pytest.fixture
def model(monkeypatch):
    """Stand in for generate_plan_result. Set `.sentence = None` to act like a fallback."""

    class FakeModel:
        calls = 0
        sentence = "Nagtanim si Lina ng palay sa bukid."

        def __init__(self):
            self.seeds = []

        def __call__(self, group, seeds=plans.SENTENCE_SEEDS):
            self.calls += 1
            self.seeds.append(seeds)
            text = f"plan {self.calls} for {group.level}"
            return PlanResult(text=text, template="word_practice", sentence=self.sentence)

    fake = FakeModel()
    monkeypatch.setattr(plan_cache, "generate_plan_result", fake)
    return fake


def test_a_plan_is_made_once_then_served_from_the_cache(model):
    assert plan_cache.get_plan(GROUP) == "plan 1 for Developing"
    assert plan_cache.get_plan(GROUP) == "plan 1 for Developing"
    assert model.calls == 1


def test_the_cache_survives_a_restart(model, storage):
    plan_cache.get_plan(GROUP)
    saved = json.loads((storage / "plan-cache.json").read_text(encoding="utf-8"))
    assert list(saved.values()) == ["plan 1 for Developing"]


@pytest.mark.parametrize("changed", [
    GroupStats(level="Transitioning", learner_count=3, common_missed_words=["palay", "bukid"]),
    GroupStats(level="Developing", learner_count=4, common_missed_words=["palay", "bukid"]),
    GroupStats(level="Developing", learner_count=3, common_missed_words=["palay"]),
    # Order matters: the plan lists the words in this order.
    GroupStats(level="Developing", learner_count=3, common_missed_words=["bukid", "palay"]),
])
def test_any_change_to_the_group_makes_a_new_plan(model, changed):
    plan_cache.get_plan(GROUP)
    plan_cache.get_plan(changed)
    assert model.calls == 2


def test_words_are_cleaned_before_keying(model):
    plan_cache.get_plan(GROUP)
    plan_cache.get_plan(GroupStats(level="Developing", learner_count=3,
                                   common_missed_words=["palay,", "bukid.", "Palay"]))
    assert model.calls == 1


def test_a_new_model_makes_a_new_plan(model, monkeypatch):
    plan_cache.get_plan(GROUP)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:14b")
    plan_cache.get_plan(GROUP)
    assert model.calls == 2


def test_editing_a_prompt_file_makes_a_new_plan(model, tmp_path, monkeypatch):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for path in plan_cache._prompt_files("fil"):
        (prompts / path.name).write_bytes(path.read_bytes())
    monkeypatch.setattr(plan_cache, "PROMPTS_DIR", prompts)

    plan_cache.get_plan(GROUP)
    (prompts / "activities-fil.json").write_text(
        (prompts / "activities-fil.json").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    plan_cache.get_plan(GROUP)

    assert model.calls == 2


def test_an_unreadable_prompt_file_skips_the_cache(model, tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(plan_cache, "PROMPTS_DIR", tmp_path / "nowhere")
    plan_cache.get_plan(GROUP)
    plan_cache.get_plan(GROUP)
    assert model.calls == 2
    assert "plan cache skipped" in caplog.text


def test_a_template_only_plan_is_not_cached(model, storage):
    model.sentence = None  # Ollama down or every try rejected
    plan_cache.get_plan(GROUP)
    plan_cache.get_plan(GROUP)
    assert model.calls == 2
    assert not (storage / "plan-cache.json").exists()


@pytest.mark.parametrize("content", ["not json", "[1, 2]", ""])
def test_a_broken_cache_file_is_treated_as_empty(model, storage, caplog, content):
    (storage / "plan-cache.json").write_text(content, encoding="utf-8")

    assert plan_cache.get_plan(GROUP) == "plan 1 for Developing"
    assert "starting empty" in caplog.text
    # ...and is replaced by a good one.
    assert plan_cache.get_plan(GROUP) == "plan 1 for Developing"
    assert model.calls == 1


def test_entries_that_are_not_text_are_ignored(model, storage):
    key = plan_cache.cache_key(GROUP)
    (storage / "plan-cache.json").write_text(json.dumps({key: 42}), encoding="utf-8")
    assert plan_cache.get_plan(GROUP) == "plan 1 for Developing"


def test_a_cache_that_cant_be_saved_still_returns_the_plan(model, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(plan_cache.os, "replace", fail)
    assert plan_cache.get_plan(GROUP) == "plan 1 for Developing"
    assert "could not be saved" in caplog.text


def test_bad_input_still_raises_plan_error(storage):
    with pytest.raises(PlanError):
        plan_cache.get_plan(GroupStats(level="Developing", learner_count=1,
                                       common_missed_words="palay"))
    with pytest.raises(PlanError):
        plan_cache.get_plan(GroupStats(level="", learner_count=1))


def test_overlapping_requests_make_the_plan_once(monkeypatch):
    calls = []

    def slow(group, seeds):
        calls.append(group)
        time.sleep(0.2)
        return PlanResult(text="plan", template="word_practice", sentence="Isang pangungusap.")

    monkeypatch.setattr(plan_cache, "generate_plan_result", slow)
    results = []
    threads = [threading.Thread(target=lambda: results.append(plan_cache.get_plan(GROUP)))
               for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == ["plan"] * 4
    assert len(calls) == 1


# --- Refresh ---------------------------------------------------------------

def test_refresh_makes_a_new_plan_with_new_seeds_and_replaces_the_old_one(model):
    plan_cache.get_plan(GROUP)
    assert plan_cache.get_plan(GROUP, refresh=True) == "plan 2 for Developing"
    assert model.seeds[0] == plans.SENTENCE_SEEDS
    assert model.seeds[1] != plans.SENTENCE_SEEDS
    assert len(model.seeds[1]) == len(plans.SENTENCE_SEEDS)
    # The new plan is what later loads get.
    assert plan_cache.get_plan(GROUP) == "plan 2 for Developing"
    assert model.calls == 2


def test_a_refresh_with_no_sentence_drops_the_old_plan(model, storage):
    plan_cache.get_plan(GROUP)
    model.sentence = None  # Ollama went down
    assert plan_cache.get_plan(GROUP, refresh=True) == "plan 2 for Developing"
    assert json.loads((storage / "plan-cache.json").read_text(encoding="utf-8")) == {}
    # The next load tries the model again instead of showing the rejected plan.
    plan_cache.get_plan(GROUP)
    assert model.calls == 3


def test_refresh_with_nothing_cached_writes_no_file_when_it_fails(model, storage):
    model.sentence = None
    plan_cache.get_plan(GROUP, refresh=True)
    assert not (storage / "plan-cache.json").exists()


def test_fresh_seeds_are_random_and_in_range():
    seeds = {plan_cache.fresh_seeds() for _ in range(5)}
    assert len(seeds) == 5
    assert all(0 <= seed < plan_cache.SEED_RANGE for group in seeds for seed in group)


# --- Ollama health -----------------------------------------------------------

class FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_ollama_up(monkeypatch):
    seen = []

    def fake(url, timeout):
        seen.append((url, timeout))
        return FakeResponse(200)

    monkeypatch.setattr(plans.urllib.request, "urlopen", fake)
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9999/")

    assert ollama_status() == "up"
    assert seen == [("http://127.0.0.1:9999/api/tags", plans.HEALTH_TIMEOUT_SEC)]


@pytest.mark.parametrize("error", [
    urllib.error.URLError("connection refused"),
    TimeoutError(),
    ValueError("unknown url type"),
])
def test_ollama_down(monkeypatch, error):
    def fake(url, timeout):
        raise error

    monkeypatch.setattr(plans.urllib.request, "urlopen", fake)
    assert ollama_status() == "down"


def test_ollama_answering_with_an_error_is_down(monkeypatch):
    monkeypatch.setattr(plans.urllib.request, "urlopen", lambda url, timeout: FakeResponse(500))
    assert ollama_status() == "down"
