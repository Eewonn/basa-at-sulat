"""Tests for group plans: activity templates plus the model's sentence (P0-BE2-3).

Ollama is faked by replacing urllib's urlopen, so these run without the model
or any network.
"""

import io
import json
import logging
import socket
import urllib.error

import pytest

from app import plan_examples
from app import plans
from app.plans import (
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_URL,
    GENERATION_OPTIONS,
    MAX_MISSED_WORDS,
    SENTENCE_SEEDS,
    GroupStats,
    OllamaSettings,
    PlanError,
    build_sentence_prompt,
    check_sentence,
    clean_missed_words,
    generate_plan,
    generate_plan_result,
    render_template,
    uses_small_words_prompt,
)

SENTENCE = "Nagtanim ng palay ang bata sa bukid."
SETTINGS = OllamaSettings()
REAL_ACTIVITIES = json.loads(
    (plans.PROMPTS_DIR / "activities-fil.json").read_text(encoding="utf-8")
)


def group(**overrides):
    values = {"level": "Developing", "learner_count": 5,
              "common_missed_words": ["palay", "ng"], "language": "fil"}
    values.update(overrides)
    return GroupStats(**values)


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def ollama(monkeypatch):
    """Fake urlopen. Set .reply (dict or bytes) or .error; read .requests after.

    .replies, if set, is used up one per call first (for testing retries).
    """

    class Fake:
        reply = {"response": SENTENCE, "total_duration": 2_500_000_000}
        error = None

        def __init__(self):
            self.requests = []
            self.replies = []

        def urlopen(self, request, timeout):
            self.requests.append((request, timeout))
            if self.error:
                raise self.error
            reply = self.replies.pop(0) if self.replies else self.reply
            body = reply if isinstance(reply, bytes) else json.dumps(reply).encode()
            return FakeResponse(body)

    fake = Fake()
    monkeypatch.setattr(plans.urllib.request, "urlopen", fake.urlopen)
    return fake


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("OLLAMA_MODEL", "OLLAMA_URL", "OLLAMA_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def activities_dir(tmp_path, monkeypatch):
    """A temp prompts folder with a copy of the real files, safe to break."""
    for name in ("activities-fil.json", "sentence-fil.txt", "sentence-small-words-fil.txt"):
        (tmp_path / name).write_text(
            (plans.PROMPTS_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    monkeypatch.setattr(plans, "PROMPTS_DIR", tmp_path)
    return tmp_path


def write_activities(folder, data):
    (folder / "activities-fil.json").write_text(json.dumps(data), encoding="utf-8")


# --- Cleaning the missed words ---------------------------------------------

def test_clean_strips_punctuation_and_spaces():
    assert clean_missed_words([" bukid. ", "“Lina,”", "puno!"]) == ["bukid", "Lina", "puno"]


def test_clean_drops_blanks_and_repeats_ignoring_case_and_keeps_order():
    words = ["palay", "", "...", "Palay", "ng", "NG", "sa"]
    assert clean_missed_words(words) == ["palay", "ng", "sa"]


def test_clean_caps_the_list():
    words = [f"salita{n}" for n in range(MAX_MISSED_WORDS + 5)]
    assert clean_missed_words(words) == words[:MAX_MISSED_WORDS]


@pytest.mark.parametrize("words", ["palay", None, ["palay", 3]])
def test_clean_rejects_non_list_of_text(words):
    with pytest.raises(PlanError, match="list of text"):
        clean_missed_words(words)


# --- The activity template -------------------------------------------------

def test_word_group_gets_word_practice_with_its_words():
    text, template, words = render_template(group(common_missed_words=["ng", "mga", "sa."]))
    assert template == "word_practice"
    assert words == ["ng", "mga", "sa"]
    assert '"ng", "mga" at "sa"' in text
    assert text.startswith("Pamagat: Hanapin ang Salita\n")


def test_single_missed_word_has_no_list_joiner():
    text, _, _ = render_template(group(common_missed_words=["palay"]))
    assert 'salitang "palay".' in text


def test_group_with_no_missed_words_gets_fluency():
    text, template, words = render_template(group(common_missed_words=[]))
    assert (template, words) == ("fluency", [])
    assert text.startswith("Pamagat: Sabayang Pagbasa\n")


def test_only_punctuation_counts_as_no_missed_words():
    assert render_template(group(common_missed_words=[".", ","]))[1] == "fluency"


def test_template_has_every_section_in_order():
    text, _, _ = render_template(group())
    lines = text.split("\n")
    steps = REAL_ACTIVITIES["word_practice"]["steps"]
    assert lines[0].startswith("Pamagat: ")
    assert lines[1].startswith("Kailangan: ")
    assert lines[2] == "Mga Hakbang:"
    assert [line[:3] for line in lines[3:3 + len(steps)]] == [
        f"{n}. " for n in range(1, len(steps) + 1)
    ]
    assert lines[-1].startswith("Pagsusuri: ")
    assert "$" not in text


@pytest.mark.parametrize("language", ["eng", "ilo", "", "FIL"])
def test_unsupported_language(language):
    with pytest.raises(PlanError, match="Supported: fil"):
        render_template(group(language=language))


@pytest.mark.parametrize("level", ["", "   ", None])
def test_empty_level(level):
    with pytest.raises(PlanError, match="'level'"):
        render_template(group(level=level))


@pytest.mark.parametrize("count", [0, -2, 2.5, "4", True])
def test_bad_learner_count(count):
    with pytest.raises(PlanError, match="learner_count"):
        render_template(group(learner_count=count))


def test_missing_activities_file(activities_dir):
    (activities_dir / "activities-fil.json").unlink()
    with pytest.raises(PlanError, match="could not read the activity templates"):
        render_template(group())


def test_activities_file_with_bad_json(activities_dir):
    (activities_dir / "activities-fil.json").write_text("{", encoding="utf-8")
    with pytest.raises(PlanError, match="not valid JSON"):
        render_template(group())


@pytest.mark.parametrize("break_it, message", [
    (lambda data: data.pop("fluency"), "'fluency' needs"),
    (lambda data: data["word_practice"].pop("check"), "'word_practice' needs"),
    (lambda data: data["word_practice"].update(steps=[]), "non-empty list"),
    (lambda data: data["labels"].pop("and"), "'labels' needs"),
])
def test_incomplete_activities_file(activities_dir, break_it, message):
    data = json.loads(json.dumps(REAL_ACTIVITIES))
    break_it(data)
    write_activities(activities_dir, data)
    with pytest.raises(PlanError, match=message):
        render_template(group())


@pytest.mark.parametrize("bad_step", ["Isulat ang $salita.", "Bayad: $"])
def test_bad_placeholder_in_template(activities_dir, bad_step):
    data = json.loads(json.dumps(REAL_ACTIVITIES))
    data["word_practice"]["steps"][0] = bad_step
    write_activities(activities_dir, data)
    with pytest.raises(PlanError, match="bad placeholder"):
        render_template(group())


# --- Checking the model's sentence -----------------------------------------

WORDS = ["palay", "ng"]


def test_good_sentence_passes():
    assert check_sentence(SENTENCE, WORDS) == SENTENCE


@pytest.mark.parametrize("raw", [
    f"  {SENTENCE}\n",
    f'"{SENTENCE}"',
    f"Sentence: {SENTENCE}",
    f"Pangungusap: “{SENTENCE}”",
])
def test_sentence_labels_quotes_and_spaces_are_removed(raw):
    assert check_sentence(raw, WORDS) == SENTENCE


def test_missed_word_is_found_ignoring_case_and_punctuation():
    assert check_sentence("Ang Palay, ay hinog na.", ["palay"])


def test_sentence_with_n_tilde_and_accents_passes():
    assert check_sentence("Si Niño ay nagtanim ng palay sa bukid.", WORDS)
    assert check_sentence("Ang palay ay nasa bukíd.", WORDS)


def test_sentence_with_cyrillic_letters_is_rejected():
    # Seen in real qwen2.5:3b output: "bumubunогkayo" with Cyrillic о and г.
    with pytest.raises(PlanError, match="non-Latin letters: го"):
        check_sentence("Nagtanim ang bata ng palay, pagkatapos bumubunогkayo.", WORDS)


@pytest.mark.parametrize("raw, found", [
    # Seen in real qwen2.5:7b output despite the prompt's "never use English".
    ("Naglalaro ang mga bata sa park ngayon.", "park"),
    ("Masayang bata siya sa paglalaro ng mga toy sa Park.", "toy, park"),
    ("Bumili ng buwan ng araw siya sa tienda.", "tienda"),
])
def test_sentence_with_english_or_spanish_words_is_rejected(raw, found):
    with pytest.raises(PlanError, match=f"non-Filipino words: {found}$"):
        check_sentence(raw, ["ng", "mga", "sa", "siya"])


def test_filipino_words_spelled_like_english_ones_pass():
    # "at" and "may" are Filipino; they must never be in FOREIGN_WORDS.
    assert check_sentence("May aso at pusa ang bata.", ["aso"])


def test_missed_word_on_the_foreign_list_is_still_allowed():
    # If the passage itself had "park", the sentence may use it.
    assert check_sentence("Naglalaro ang mga bata sa park.", ["park"])


@pytest.mark.parametrize("raw, message", [
    (None, "no 'response' text"),
    ("   ", "empty"),
    ('""', "empty"),
    (f"{SENTENCE}\nIto ay isang pangungusap.", "more than one line"),
    ("Ang palay.", "had 2 words"),
    (" ".join(["palay"] + ["salita"] * 25), "had 26 words"),
    ("mga mga kahoy mga mga kahoy mga mga kahoy palay", "repeats itself"),
    ("Masaya ang bata sa paaralan.", "none of the missed words"),
    ("Ang palayok ay nasa kusina.", "none of the missed words"),
])
def test_bad_sentences_are_rejected(raw, message):
    with pytest.raises(PlanError, match=message):
        check_sentence(raw, WORDS)


def test_sentence_prompt_lists_the_words():
    prompt = build_sentence_prompt(["Nagtanim", "mga"], "fil")
    assert "Use at least one of these words, spelled exactly as given: Nagtanim, mga" in prompt
    assert "Filipino (Tagalog) words only" in prompt
    assert "$" not in prompt


@pytest.mark.parametrize("words, small", [
    (["ng", "mga", "sa", "siya"], True),
    (["NG", "Siya"], True),
    (["ng", "palay"], False),   # one content word is enough for the general prompt
    (["Nagtanim"], False),
    ([], False),
])
def test_small_words_prompt_is_only_for_function_words(words, small):
    assert uses_small_words_prompt(words, "fil") is small


def test_small_words_prompt_gives_a_word_list_and_lists_the_words():
    prompt = build_sentence_prompt(["ng", "siya"], "fil")
    assert "these small words, spelled exactly as given: ng, siya" in prompt
    assert "ONLY from these words" in prompt
    assert "$" not in prompt


def test_unknown_language_never_uses_the_small_words_prompt():
    assert uses_small_words_prompt(["ng"], "ilo") is False


@pytest.mark.parametrize("name, words", [
    ("sentence-fil.txt", ["palay"]),
    ("sentence-small-words-fil.txt", ["ng"]),
])
def test_missing_sentence_prompt(activities_dir, name, words):
    (activities_dir / name).unlink()
    with pytest.raises(PlanError, match="could not read the prompt"):
        build_sentence_prompt(words, "fil")


# --- Settings --------------------------------------------------------------

def test_default_settings():
    settings = OllamaSettings.from_env()
    assert (settings.model, settings.url, settings.timeout_sec) == (
        DEFAULT_MODEL, DEFAULT_URL, DEFAULT_TIMEOUT_SEC
    )
    assert DEFAULT_MODEL == "qwen2.5:7b"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9999/")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "30")
    settings = OllamaSettings.from_env()
    assert (settings.model, settings.url, settings.timeout_sec) == (
        "qwen2.5:3b", "http://127.0.0.1:9999", 30.0
    )


@pytest.mark.parametrize("value", ["soon", "0", "-5"])
def test_bad_timeout_env(monkeypatch, value):
    monkeypatch.setenv("OLLAMA_TIMEOUT", value)
    with pytest.raises(PlanError, match="OLLAMA_TIMEOUT"):
        OllamaSettings.from_env()


# --- Whole plans: happy path -----------------------------------------------

def test_plan_is_template_plus_model_sentence(ollama):
    result = generate_plan_result(group(), SETTINGS)
    template_text, _, _ = render_template(group())
    assert result.text == (
        f"{template_text}\nHalimbawang pangungusap (basahin nang malakas): {SENTENCE}"
    )
    assert (result.template, result.sentence, result.fallback_reason) == (
        "word_practice", SENTENCE, None
    )
    assert result.reply["total_duration"] == 2_500_000_000
    assert generate_plan(group(), SETTINGS) == result.text


def test_plan_sends_the_right_request(ollama):
    generate_plan(group(), OllamaSettings(model="qwen2.5:3b", timeout_sec=45))
    assert len(ollama.requests) == 1
    request, timeout = ollama.requests[0]
    body = json.loads(request.data)
    assert request.full_url == f"{DEFAULT_URL}/api/generate"
    assert request.get_method() == "POST"
    assert timeout == 45
    assert body["model"] == "qwen2.5:3b"
    assert body["stream"] is False
    assert body["options"] == {**GENERATION_OPTIONS, "seed": SENTENCE_SEEDS[0]}
    assert body["prompt"] == build_sentence_prompt(["palay", "ng"], "fil")


def test_plan_reads_settings_from_env_when_none_given(ollama, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "custom:1b")
    generate_plan(group())
    assert json.loads(ollama.requests[0][0].data)["model"] == "custom:1b"


def test_fluency_plan_never_calls_the_model(ollama):
    result = generate_plan_result(group(common_missed_words=[]), SETTINGS)
    assert ollama.requests == []
    assert (result.template, result.sentence, result.fallback_reason) == ("fluency", None, None)
    assert "Halimbawang pangungusap" not in result.text


def test_bad_input_raises_and_never_calls_the_model(ollama):
    with pytest.raises(PlanError):
        generate_plan(group(language="eng"), SETTINGS)
    assert ollama.requests == []


def sent_seeds(ollama):
    return [json.loads(request.data)["options"]["seed"] for request, _ in ollama.requests]


def test_rejected_sentence_is_retried_with_the_next_seed(ollama):
    ollama.replies = [{"response": "Naglalaro ang bata ng palay sa park."}]
    result = generate_plan_result(group(), SETTINGS)
    assert sent_seeds(ollama) == list(SENTENCE_SEEDS[:2])
    assert (result.sentence, result.tries, result.fallback_reason) == (SENTENCE, 2, None)


def test_rejected_tries_are_logged(ollama, caplog):
    ollama.replies = [{"response": "Ang palay sa park."}]
    with caplog.at_level(logging.INFO, logger="app.plans"):
        generate_plan(group(), SETTINGS)
    assert "sentence try 1 (seed 42) rejected" in caplog.text


# --- Whole plans: the model fails, the template still comes back -----------

def http_error(code, reason="error"):
    return urllib.error.HTTPError(f"{DEFAULT_URL}/api/generate", code, reason, {},
                                  io.BytesIO(b""))


@pytest.mark.parametrize("error, reason", [
    (http_error(404, "Not Found"), "ollama pull qwen2.5:7b"),
    (http_error(500, "Internal Server Error"), "HTTP 500"),
    (urllib.error.URLError(ConnectionRefusedError(10061, "refused")), "ollama serve"),
    (TimeoutError("timed out"), "longer than 120 s"),
    (socket.timeout("timed out"), "longer than 120 s"),
    (urllib.error.URLError(TimeoutError("timed out")), "longer than 120 s"),
])
def test_ollama_errors_fall_back_to_the_template(ollama, error, reason):
    ollama.error = error
    result = generate_plan_result(group(), SETTINGS)
    assert result.text == render_template(group())[0]
    assert result.sentence is None
    assert reason in result.fallback_reason
    # Another seed can't fix an Ollama problem, so it isn't retried.
    assert len(ollama.requests) == 1


@pytest.mark.parametrize("reply, reason", [
    (b"not json", "not valid JSON"),
    (b"\xff\xfe", "not valid JSON"),
    (b"[1, 2]", "not a JSON object"),
])
def test_unreadable_replies_fall_back_without_retrying(ollama, reply, reason):
    ollama.reply = reply
    result = generate_plan_result(group(), SETTINGS)
    assert result.text == render_template(group())[0]
    assert reason in result.fallback_reason
    assert len(ollama.requests) == 1


@pytest.mark.parametrize("reply, reason", [
    ({"done": True}, "no 'response' text"),
    ({"response": "   \n "}, "empty"),
    ({"response": "Masaya ang bata sa paaralan."}, "none of the missed words"),
    ({"response": "Naglalaro ang bata ng palay sa park."}, "non-Filipino words: park"),
])
def test_rejected_on_every_seed_falls_back_to_the_template(ollama, reply, reason):
    ollama.reply = reply
    result = generate_plan_result(group(), SETTINGS)
    assert result.text == render_template(group())[0]
    assert sent_seeds(ollama) == list(SENTENCE_SEEDS)
    assert f"all {len(SENTENCE_SEEDS)} tries were rejected; last: " in result.fallback_reason
    assert reason in result.fallback_reason


def test_bad_timeout_env_falls_back_too(ollama, monkeypatch):
    # A typo in a setting shouldn't cost the teacher the whole plan.
    monkeypatch.setenv("OLLAMA_TIMEOUT", "soon")
    result = generate_plan_result(group())
    assert "OLLAMA_TIMEOUT" in result.fallback_reason
    assert ollama.requests == []


def test_fallback_is_logged_not_silent(ollama, caplog):
    ollama.error = urllib.error.URLError(ConnectionRefusedError(10061, "refused"))
    with caplog.at_level(logging.WARNING, logger="app.plans"):
        generate_plan(group(), SETTINGS)
    assert "no example sentence" in caplog.text
    assert "ollama serve" in caplog.text


# --- Example generator -----------------------------------------------------

def write_inputs(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_shipped_inputs_are_three_filipino_groups():
    groups = plan_examples.load_groups(plan_examples.DEFAULT_INPUTS_PATH)
    assert len(groups) == 3
    assert all(stats.language == "fil" for _, stats in groups)
    # Each one must render, so a typo in inputs.json fails here, not at demo time.
    templates = [render_template(stats)[1] for _, stats in groups]
    assert templates == ["word_practice", "word_practice", "fluency"]


def test_generator_writes_one_file_per_group(ollama, tmp_path):
    inputs = write_inputs(tmp_path / "inputs.json", [
        {"name": "a", "level": "Developing", "learner_count": 2,
         "common_missed_words": ["palay."]},
        {"level": "At Grade Level", "learner_count": 3, "common_missed_words": []},
    ])
    paths = plan_examples.generate_examples(inputs, tmp_path / "out", SETTINGS)
    assert [path.name for path in paths] == ["example-1.md", "example-2.md"]

    first = paths[0].read_text(encoding="utf-8")
    assert "# Example 1: a group" in first
    assert "Missed words: palay\n" in first
    assert "`qwen2.5:7b` via Ollama" in first
    assert "seed 42 (try 1 of 3)" in first
    assert "Model time for the kept try: 2.5 s" in first
    assert SENTENCE in first
    second = paths[1].read_text(encoding="utf-8")
    assert "# Example 2: group 2 group" in second
    assert "fluency activities don't use the model" in second
    assert "Sabayang Pagbasa" in second


def test_generator_refuses_examples_without_the_model_sentence(ollama, tmp_path):
    ollama.error = urllib.error.URLError(ConnectionRefusedError(10061, "refused"))
    out = tmp_path / "out"
    with pytest.raises(PlanError, match=r"example 1 \(struggling\) has no model sentence"):
        plan_examples.generate_examples(plan_examples.DEFAULT_INPUTS_PATH, out, SETTINGS)
    assert not out.exists()


def test_generator_writes_nothing_if_a_later_group_is_invalid(ollama, tmp_path):
    inputs = write_inputs(tmp_path / "inputs.json", [
        {"level": "Developing", "learner_count": 2, "common_missed_words": ["palay"]},
        {"level": "Developing", "learner_count": 2, "common_missed_words": [],
         "language": "eng"},
    ])
    out = tmp_path / "out"
    with pytest.raises(PlanError, match="Supported: fil"):
        plan_examples.generate_examples(inputs, out, SETTINGS)
    assert not out.exists()


@pytest.mark.parametrize("data, message", [
    ([], "non-empty list"),
    ({"level": "x"}, "non-empty list"),
    (["x"], "entry 0 is not an object"),
    ([{"level": "x", "learner_count": 1}], "missing common_missed_words"),
])
def test_generator_rejects_bad_inputs(tmp_path, data, message):
    inputs = write_inputs(tmp_path / "inputs.json", data)
    with pytest.raises(PlanError, match=message):
        plan_examples.load_groups(inputs)


def test_generator_cli_reports_errors(ollama, tmp_path, capsys):
    ollama.error = urllib.error.URLError(ConnectionRefusedError(10061, "refused"))
    code = plan_examples.main(["--inputs", str(plan_examples.DEFAULT_INPUTS_PATH),
                               "--out", str(tmp_path / "out")])
    assert code == 1
    assert "ollama serve" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_generator_cli_missing_inputs(tmp_path, capsys):
    code = plan_examples.main(["--inputs", str(tmp_path / "nope.json")])
    assert code == 1
    assert "file not found" in capsys.readouterr().err
