"""Draft a small-group reading activity for the class view (P0-BE2-3).

A plan is a teacher-written activity template (prompts/activities-<lang>.json)
filled with the group's missed words. The local model (qwen2.5:7b in Ollama)
adds one thing: an example sentence that uses those words, for the teacher to
read aloud. The sentence is only kept if it passes basic checks.

Why templates first: small models write garbled or repetitive Filipino when
they plan a whole activity, but a 7B model handles one short sentence
(docs/DECISIONS.md). If Ollama is down or every try fails the checks, the
plan is the template alone, so the class view never shows a blank or garbled
plan.

Filipino only for now. Adding a language means adding activities-<code>.json
and sentence-<code>.txt and the code to SUPPORTED_LANGUAGES.
"""

import json
import logging
import os
import socket
import string
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from app.db import ENGINE_DIR

logger = logging.getLogger(__name__)

PROMPTS_DIR = ENGINE_DIR / "prompts"
SUPPORTED_LANGUAGES = ("fil",)

# Apache 2.0, unlike qwen2.5:3b's research-only license (docs/DECISIONS.md).
DEFAULT_MODEL = "qwen2.5:7b"
# 127.0.0.1, not localhost: nothing in this app should ever leave the laptop.
DEFAULT_URL = "http://127.0.0.1:11434"
# A 7B model on a laptop CPU can take tens of seconds on a cold start.
DEFAULT_TIMEOUT_SEC = 120.0

# More words than this makes the activity unfocused.
MAX_MISSED_WORDS = 10

# Low temperature keeps the sentence close to the prompt. num_predict caps the
# length (one sentence), and repeat_penalty stops the word loops seen in testing.
# The seed is added per try (SENTENCE_SEEDS).
GENERATION_OPTIONS = {"temperature": 0.3, "num_predict": 60, "repeat_penalty": 1.15}

# A rejected sentence is retried with the next seed: a different seed often
# gives a clean sentence where the first slipped in an English word. Fixed
# seeds keep the result mostly stable (CPU runs aren't fully deterministic).
# Only rejections are retried; if Ollama is down, retrying just wastes time.
SENTENCE_SEEDS = (42, 1, 2)

# Limits for the model's sentence. A longer or shorter reply is usually the
# model explaining itself or breaking down, not a sentence for a child.
SENTENCE_MIN_WORDS = 3
SENTENCE_MAX_WORDS = 20

# English (and Spanish) words the 7B model slipped into Filipino sentences in
# testing, despite the prompt, plus common English function words. Not a full
# dictionary: it catches the usual slips. Words that are also Filipino
# ("at", "may", "na") must never be added here.
FOREIGN_WORDS = frozenset({
    "the", "and", "is", "are", "of", "to", "in", "with", "for", "this", "that",
    "park", "toy", "toys", "school", "store", "supermarket", "community", "mall",
    "house", "friend", "friends", "family", "teacher", "book", "ball", "happy",
    "play", "bed", "tienda",
})

# Function words (markers, pronouns, linkers). A group that missed only these
# gets the small-words prompt. Draft list: needs native-speaker review.
SMALL_WORDS = {
    "fil": frozenset({
        "ang", "ng", "nang", "sa", "si", "ni", "kay", "sina", "nina", "kina",
        "mga", "ay", "at", "na", "o", "pero", "kung", "para", "dahil",
        "ako", "ko", "ikaw", "ka", "mo", "siya", "niya", "kami", "namin",
        "tayo", "natin", "kayo", "ninyo", "sila", "nila", "ito", "iyan", "iyon",
        "dito", "diyan", "doon", "may", "hindi", "din", "rin", "lang", "po",
        "ba", "pa", "nga", "naman",
    }),
}

# Passage words keep their punctuation ("bukid."), so it's stripped before
# words reach the plan. Includes the curly quotes and marks seen in passages.
PUNCTUATION = string.punctuation + "“”‘’«»¿¡…"

TEMPLATE_KEYS = ("title", "materials", "steps", "check")
LABEL_KEYS = ("title", "materials", "steps", "check", "sentence", "and")


class PlanError(Exception):
    """The plan or the model's sentence couldn't be made. The message says what to fix."""


@dataclass
class GroupStats:
    """One group in the class view (GET /class in docs/API.md)."""

    level: str
    learner_count: int
    common_missed_words: list[str] = field(default_factory=list)
    language: str = "fil"


@dataclass
class OllamaSettings:
    """Where and how to reach Ollama. Environment variables override the defaults."""

    model: str = DEFAULT_MODEL
    url: str = DEFAULT_URL
    timeout_sec: float = DEFAULT_TIMEOUT_SEC

    @classmethod
    def from_env(cls) -> "OllamaSettings":
        raw_timeout = os.environ.get("OLLAMA_TIMEOUT")
        if raw_timeout is None:
            timeout = DEFAULT_TIMEOUT_SEC
        else:
            try:
                timeout = float(raw_timeout)
            except ValueError:
                raise PlanError(
                    f"OLLAMA_TIMEOUT must be a number of seconds, got '{raw_timeout}'"
                ) from None
            if timeout <= 0:
                raise PlanError(f"OLLAMA_TIMEOUT must be greater than 0, got {timeout}")
        return cls(
            model=os.environ.get("OLLAMA_MODEL") or DEFAULT_MODEL,
            url=(os.environ.get("OLLAMA_URL") or DEFAULT_URL).rstrip("/"),
            timeout_sec=timeout,
        )


@dataclass
class PlanResult:
    """A plan plus how it was made, for the saved examples and for logging."""

    text: str
    template: str                      # "word_practice" or "fluency"
    sentence: str | None = None        # the model's sentence, if it was kept
    fallback_reason: str | None = None  # why there's no sentence, if there isn't
    reply: dict | None = None          # Ollama's raw reply for the kept try, for timings
    tries: int = 0                     # model calls made (more than 1 means rejections)


# --- Checking and cleaning the input ---------------------------------------

def clean_missed_words(words) -> list[str]:
    """Strip punctuation, drop blanks and repeats (ignoring case), keep order, cap the list."""
    if not isinstance(words, list) or not all(isinstance(word, str) for word in words):
        raise PlanError("'common_missed_words' must be a list of text")

    cleaned, seen = [], set()
    for word in words:
        word = word.strip().strip(PUNCTUATION)
        key = word.casefold()
        if word and key not in seen:
            seen.add(key)
            cleaned.append(word)
    return cleaned[:MAX_MISSED_WORDS]


def _check_group(group: GroupStats) -> None:
    if group.language not in SUPPORTED_LANGUAGES:
        raise PlanError(
            f"plans aren't available in '{group.language}' yet. "
            f"Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        )
    if not isinstance(group.level, str) or not group.level.strip():
        raise PlanError("'level' must be non-empty text")
    count = group.learner_count
    # bool is a subclass of int, so `True` would otherwise pass as 1 learner.
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise PlanError("'learner_count' must be a whole number from 1")


# --- The activity template -------------------------------------------------

def load_activities(language: str) -> dict:
    """Read and check prompts/activities-<language>.json."""
    path = PROMPTS_DIR / f"activities-{language}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise PlanError(f"could not read the activity templates {path}: {err}") from None
    except json.JSONDecodeError as err:
        raise PlanError(f"{path} is not valid JSON: {err}") from None

    # A broken template should fail loudly here, not show a half-empty plan.
    for name in ("word_practice", "fluency"):
        activity = data.get(name)
        if not isinstance(activity, dict) or any(key not in activity for key in TEMPLATE_KEYS):
            raise PlanError(f"{path}: '{name}' needs {', '.join(TEMPLATE_KEYS)}")
        if not isinstance(activity["steps"], list) or not activity["steps"]:
            raise PlanError(f"{path}: '{name}.steps' must be a non-empty list")
    labels = data.get("labels")
    if not isinstance(labels, dict) or any(key not in labels for key in LABEL_KEYS):
        raise PlanError(f"{path}: 'labels' needs {', '.join(LABEL_KEYS)}")
    return data


def _join_words(words: list[str], and_word: str) -> str:
    """'"ng", "mga" at "sa"': quoted, so the teacher sees exactly what to write."""
    quoted = [f'"{word}"' for word in words]
    if len(quoted) == 1:
        return quoted[0]
    return f"{', '.join(quoted[:-1])} {and_word} {quoted[-1]}"


def render_template(group: GroupStats) -> tuple[str, str, list[str]]:
    """Return (plan text, template name, cleaned missed words) without calling the model."""
    _check_group(group)
    words = clean_missed_words(group.common_missed_words)
    data = load_activities(group.language)
    labels = data["labels"]
    name = "word_practice" if words else "fluency"
    activity = data[name]

    fill = {"words": _join_words(words, labels["and"]) if words else ""}
    try:
        steps = [string.Template(step).substitute(fill) for step in activity["steps"]]
        lines = [
            f"{labels['title']}: {string.Template(activity['title']).substitute(fill)}",
            f"{labels['materials']}: {string.Template(activity['materials']).substitute(fill)}",
            f"{labels['steps']}:",
            *(f"{number}. {step}" for number, step in enumerate(steps, start=1)),
            f"{labels['check']}: {string.Template(activity['check']).substitute(fill)}",
        ]
    except (KeyError, ValueError) as err:
        # An unknown $placeholder or a stray "$" in the JSON.
        raise PlanError(f"activity template '{name}' has a bad placeholder: {err}") from None
    return "\n".join(lines), name, words


# --- The model's example sentence ------------------------------------------

def uses_small_words_prompt(words: list[str], language: str) -> bool:
    """True if every missed word is a small function word (ng, sa, mga, siya...)."""
    small = SMALL_WORDS.get(language, frozenset())
    return bool(words) and all(word.casefold() in small for word in words)


def build_sentence_prompt(words: list[str], language: str) -> str:
    # With only function words to go on, the general prompt gave nonsense like
    # "Siya ay may mga kapatid sa paglalaro sa hulugan." A prompt that fixes
    # the topic (one child, one everyday action) gives the model a frame.
    if uses_small_words_prompt(words, language):
        path = PROMPTS_DIR / f"sentence-small-words-{language}.txt"
    else:
        path = PROMPTS_DIR / f"sentence-{language}.txt"
    try:
        template = string.Template(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise PlanError(f"could not read the prompt {path}: {err}") from None
    return template.substitute(words=", ".join(words))


def _post_generate(prompt: str, settings: OllamaSettings, seed: int) -> dict:
    """POST to Ollama's /api/generate and return the decoded JSON reply."""
    payload = json.dumps({
        "model": settings.model,
        "prompt": prompt,
        "stream": False,
        "options": {**GENERATION_OPTIONS, "seed": seed},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_sec) as response:
            body = response.read()
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise PlanError(
                f"Ollama doesn't have the model '{settings.model}'. "
                f"Run `ollama pull {settings.model}` once, while online."
            ) from None
        raise PlanError(f"Ollama returned HTTP {err.code}: {err.reason}") from None
    except (TimeoutError, socket.timeout):
        raise PlanError(
            f"Ollama took longer than {settings.timeout_sec:g} s. "
            "Raise OLLAMA_TIMEOUT, or check the laptop isn't busy."
        ) from None
    except urllib.error.URLError as err:
        # A timeout while connecting arrives wrapped in URLError.
        if isinstance(err.reason, (TimeoutError, socket.timeout)):
            raise PlanError(
                f"Ollama took longer than {settings.timeout_sec:g} s to answer."
            ) from None
        raise PlanError(
            f"could not reach Ollama at {settings.url} ({err.reason}). "
            "Is it running? Start it with `ollama serve`."
        ) from None

    try:
        reply = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PlanError("Ollama's reply was not valid JSON") from None
    if not isinstance(reply, dict):
        raise PlanError("Ollama's reply was not a JSON object")
    return reply


def check_sentence(raw, words: list[str]) -> str:
    """Return the cleaned sentence, or raise PlanError saying why it was rejected.

    These checks catch the failures seen in testing (rambling, loops, ignoring
    the words). They can't judge whether the Filipino is natural: that's what
    the native-speaker review of the examples is for.
    """
    if not isinstance(raw, str):
        raise PlanError("Ollama's reply had no 'response' text")
    sentence = raw.strip()
    # Small models often add a label or quotes despite being told not to.
    for prefix in ("Sentence:", "Pangungusap:"):
        if sentence.startswith(prefix):
            sentence = sentence[len(prefix):].strip()
    sentence = sentence.strip("\"'“”‘’ ")

    if not sentence:
        raise PlanError("the model's sentence was empty")
    if "\n" in sentence:
        raise PlanError("the model wrote more than one line")
    # Filipino uses the Latin alphabet (with ñ and accents). The 3B model has
    # produced words with Cyrillic letters mixed in, which a child can't read.
    foreign = sorted({char for char in sentence
                      if char.isalpha() and "LATIN" not in unicodedata.name(char, "")})
    if foreign:
        raise PlanError(f"the model's sentence has non-Latin letters: {''.join(foreign)}")
    tokens = sentence.split()
    if not SENTENCE_MIN_WORDS <= len(tokens) <= SENTENCE_MAX_WORDS:
        raise PlanError(
            f"the model's sentence had {len(tokens)} words "
            f"(allowed: {SENTENCE_MIN_WORDS}-{SENTENCE_MAX_WORDS})"
        )
    lowered = [token.strip(PUNCTUATION).casefold() for token in tokens]
    if len(set(lowered)) < len(lowered) / 2:
        raise PlanError("the model's sentence repeats itself")
    # A missed word is never rejected as foreign: the passage chose it.
    allowed = {word.casefold() for word in words}
    foreign_words = [token for token in lowered
                     if token in FOREIGN_WORDS and token not in allowed]
    if foreign_words:
        raise PlanError(f"the model's sentence has non-Filipino words: {', '.join(foreign_words)}")
    if not any(word.casefold() in lowered for word in words):
        raise PlanError("the model's sentence uses none of the missed words")
    return sentence


def generate_sentence(words: list[str], language: str,
                      settings: OllamaSettings) -> tuple[str, dict, int]:
    """Ask the model for one example sentence, retrying rejections with the next seed.

    Returns (sentence, reply, tries). Raises PlanError if Ollama fails, or if
    every seed's sentence is rejected (the message gives the last reason).
    """
    prompt = build_sentence_prompt(words, language)
    for tries, seed in enumerate(SENTENCE_SEEDS, start=1):
        # Errors reaching Ollama propagate at once: another seed won't help.
        reply = _post_generate(prompt, settings, seed)
        try:
            return check_sentence(reply.get("response"), words), reply, tries
        except PlanError as err:
            logger.info("sentence try %d (seed %d) rejected: %s", tries, seed, err)
            last_error = err
    raise PlanError(f"all {len(SENTENCE_SEEDS)} tries were rejected; last: {last_error}")


# --- Putting it together ---------------------------------------------------

def generate_plan_result(group: GroupStats,
                         settings: OllamaSettings | None = None) -> PlanResult:
    """Build the plan from its template, then try to add the model's sentence.

    Raises PlanError only for bad input or a broken template file. Anything
    that goes wrong with the model is logged and the template-only plan is
    returned, because a plan without a sentence is still useful.
    """
    text, template, words = render_template(group)
    if not words:
        # A fluency activity has no words to build a sentence around.
        return PlanResult(text=text, template=template)

    try:
        settings = settings or OllamaSettings.from_env()
        sentence, reply, tries = generate_sentence(words, group.language, settings)
    except PlanError as err:
        logger.warning("group plan for level '%s' has no example sentence: %s",
                       group.level, err)
        return PlanResult(text=text, template=template, fallback_reason=str(err))

    labels = load_activities(group.language)["labels"]
    return PlanResult(
        text=f"{text}\n{labels['sentence']}: {sentence}",
        template=template,
        sentence=sentence,
        reply=reply,
        tries=tries,
    )


def generate_plan(group: GroupStats, settings: OllamaSettings | None = None) -> str:
    """Return the `draft_plan` text for one group, in the group's language."""
    return generate_plan_result(group, settings).text
