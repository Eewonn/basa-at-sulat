"""Cached group plans for the class view (P2-BE2-3).

A plan with a model sentence takes qwen2.5:7b tens of seconds on a laptop CPU,
so GET /class would be slow on every load without this. A plan is stored under
a key made of everything that changes its text: language, model, level,
learner count, the missed words in order, and the prompt files' contents (so
a native speaker's edit to the templates makes new plans).

The cache is a JSON file in storage_dir() (git-ignored), so it survives a
restart without a schema change. Only plans with a model sentence are stored:
a template-only plan (Ollama down, every try rejected) is returned but not
kept, so a later load can still get a sentence.

A missing, unreadable or broken cache file is logged and treated as empty.
The cache never stops a plan from being returned.
"""

import hashlib
import json
import logging
import os
import random
import threading
from pathlib import Path

from app.audio import storage_dir
from app.plans import (
    DEFAULT_MODEL,
    PROMPTS_DIR,
    SENTENCE_SEEDS,
    GroupStats,
    PlanError,
    clean_missed_words,
    generate_plan_result,
)

logger = logging.getLogger(__name__)

CACHE_FILE_NAME = "plan-cache.json"
# Ollama takes any 32-bit seed.
SEED_RANGE = 2**31

# Guards _key_locks and every read-modify-write of the file.
_file_lock = threading.Lock()
# One lock per key, so two overlapping GET /class requests don't both run
# Ollama for the same group, while different groups don't wait on each other.
_key_locks: dict[str, threading.Lock] = {}


def cache_path() -> Path:
    return storage_dir() / CACHE_FILE_NAME


def _prompt_files(language: str) -> list[Path]:
    return [
        PROMPTS_DIR / f"activities-{language}.json",
        PROMPTS_DIR / f"sentence-{language}.txt",
        PROMPTS_DIR / f"sentence-small-words-{language}.txt",
    ]


def _prompts_hash(language: str) -> str | None:
    """A hash of the language's prompt files, or None if one can't be read."""
    digest = hashlib.sha256()
    for path in _prompt_files(language):
        try:
            digest.update(path.read_bytes())
        except OSError as err:
            logger.warning("plan cache skipped: could not read %s: %s", path, err)
            return None
    return digest.hexdigest()


def cache_key(group: GroupStats) -> str | None:
    """The key for this group's plan, or None if the plan shouldn't be cached.

    Words keep their order (the plan lists them in that order), so the same
    words ranked differently make a separate entry.
    """
    prompts = _prompts_hash(group.language)
    if prompts is None:
        return None
    model = os.environ.get("OLLAMA_MODEL") or DEFAULT_MODEL
    try:
        words = clean_missed_words(group.common_missed_words)
    except PlanError:
        return None  # bad input: generate_plan_result raises it with the full message
    raw = json.dumps(
        [group.language, model, group.level, group.learner_count, words, prompts],
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_cache() -> dict[str, str]:
    path = cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        logger.warning("plan cache %s could not be read, starting empty: %s", path, err)
        return {}
    if not isinstance(data, dict):
        logger.warning("plan cache %s is not a JSON object, starting empty", path)
        return {}
    # Drop anything that isn't text, rather than serve it as a plan.
    return {key: value for key, value in data.items() if isinstance(value, str)}


def _write_cache(data: dict[str, str]) -> None:
    path = cache_path()
    tmp = path.with_suffix(".json.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        # Replace in one step, so a crash mid-write never leaves a half-written cache.
        os.replace(tmp, path)
    except OSError as err:
        logger.warning("plan cache %s could not be saved: %s", path, err)


def _lock_for(key: str) -> threading.Lock:
    with _file_lock:
        return _key_locks.setdefault(key, threading.Lock())


def fresh_seeds() -> tuple[int, ...]:
    """Random seeds for a refresh. The fixed SENTENCE_SEEDS would give back the same sentence."""
    rng = random.SystemRandom()
    return tuple(rng.randrange(SEED_RANGE) for _ in SENTENCE_SEEDS)


def _update_cache(key: str, text: str | None) -> None:
    """Store a plan under key, or remove the entry if text is None."""
    with _file_lock:
        data = _read_cache()
        if text is None:
            if data.pop(key, None) is None:
                return  # nothing to remove: don't rewrite the file
        else:
            data[key] = text
        _write_cache(data)


def get_plan(group: GroupStats, refresh: bool = False) -> str:
    """Return the group's draft plan, from the cache if it's there.

    With refresh=True the cached plan is skipped and a new one is made with
    new seeds, for a teacher who doesn't like the example sentence. If the new
    try has no sentence (Ollama down, every try rejected), the old plan is
    still dropped: the teacher rejected it, and the next load tries again.

    Raises PlanError only for bad input or a broken template file, like
    plans.generate_plan.
    """
    seeds = fresh_seeds() if refresh else SENTENCE_SEEDS
    key = cache_key(group)
    if key is None:
        return generate_plan_result(group, seeds=seeds).text

    with _lock_for(key):
        if not refresh:
            # Checked inside the key's lock: a request that waited on another
            # one making this plan finds it here instead of making it again.
            with _file_lock:
                cached = _read_cache().get(key)
            if cached is not None:
                return cached

        result = generate_plan_result(group, seeds=seeds)
        if result.sentence is None:
            # Template-only plans are cheap to remake and may get a sentence next time.
            if refresh:
                _update_cache(key, None)
            return result.text

        _update_cache(key, result.text)
        return result.text
