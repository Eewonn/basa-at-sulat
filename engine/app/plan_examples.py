"""Generate the saved group-plan examples (P0-BE2-3).

Run from engine/, with Ollama running and the model pulled:
    python -m app.plan_examples

Reads prompts/examples/inputs.json and writes example-1.md, example-2.md...
next to it. Every plan is generated before any file is written, so a failure
partway never leaves a mix of old and new examples.

In the app, a plan whose model sentence fails falls back to the template
alone. Here that's an error instead: an example without the sentence it was
supposed to show (because Ollama was off, say) isn't worth saving.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.plans import (
    GENERATION_OPTIONS,
    PROMPTS_DIR,
    SENTENCE_SEEDS,
    GroupStats,
    OllamaSettings,
    PlanError,
    PlanResult,
    clean_missed_words,
    generate_plan_result,
)

EXAMPLES_DIR = PROMPTS_DIR / "examples"
DEFAULT_INPUTS_PATH = EXAMPLES_DIR / "inputs.json"
GROUP_FIELDS = ("level", "learner_count", "common_missed_words")


def load_groups(path: Path) -> list[tuple[str, GroupStats]]:
    """Read the example inputs as (name, GroupStats) pairs, or raise PlanError."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PlanError(f"{path}: file not found") from None
    except (OSError, json.JSONDecodeError) as err:
        raise PlanError(f"{path}: could not read: {err}") from None

    if not isinstance(data, list) or not data:
        raise PlanError(f"{path}: expected a non-empty list of groups")

    groups = []
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise PlanError(f"{path}: entry {index} is not an object")
        missing = [name for name in GROUP_FIELDS if name not in entry]
        if missing:
            raise PlanError(f"{path}: entry {index}: missing {', '.join(missing)}")
        groups.append((
            entry.get("name", f"group {index + 1}"),
            GroupStats(
                level=entry["level"],
                learner_count=entry["learner_count"],
                common_missed_words=entry["common_missed_words"],
                language=entry.get("language", "fil"),
            ),
        ))
    return groups


def _seconds(reply: dict, key: str) -> str:
    # Ollama reports durations in nanoseconds.
    value = reply.get(key)
    return f"{value / 1e9:.1f} s" if isinstance(value, (int, float)) else "not reported"


def _how_it_was_made(result: PlanResult, settings: OllamaSettings) -> str:
    template = f"- Activity template: `{result.template}` (prompts/activities-fil.json)\n"
    if result.sentence is None:
        # Only fluency plans get here: word-practice fallbacks stop the run.
        return template + "- Example sentence: none (fluency activities don't use the model)\n"
    reply = result.reply or {}
    # Earlier tries were rejected by check_sentence (logged at INFO).
    seed = SENTENCE_SEEDS[result.tries - 1] if result.tries else "?"
    return (
        template
        + f"- Example sentence: `{settings.model}` via Ollama, "
        f"options `{json.dumps(GENERATION_OPTIONS)}`, seed {seed} "
        f"(try {result.tries} of {len(SENTENCE_SEEDS)})\n"
        f"- Model time for the kept try: {_seconds(reply, 'total_duration')} "
        f"(model load: {_seconds(reply, 'load_duration')})\n"
    )


def render_example(number: int, name: str, group: GroupStats, result: PlanResult,
                   settings: OllamaSettings, generated_at: str) -> str:
    """One example file: what went in, how it was made, and what came out."""
    # Show the words as the plan received them (punctuation stripped, capped).
    words = ", ".join(clean_missed_words(group.common_missed_words)) or "none"
    return (
        f"# Example {number}: {name} group\n\n"
        "## Input\n"
        f"- Level: {group.level} (provisional: names are checked against CRLA in P1-BE2-2)\n"
        f"- Learners: {group.learner_count}\n"
        f"- Missed words: {words}\n"
        f"- Language: {group.language}\n\n"
        "## How it was made\n"
        f"{_how_it_was_made(result, settings)}"
        f"- Generated: {generated_at}\n\n"
        "## Draft plan (as the class view shows it)\n\n"
        f"{result.text}\n\n"
        "## Native-speaker review\n"
        "- Reviewed by: _pending_\n"
        "- Template wording is natural Filipino: _pending_\n"
        "- Example sentence is natural Filipino and fits the level: _pending_\n"
        "- Runnable in about 10 minutes: _pending_\n"
    )


def generate_examples(inputs_path: Path = DEFAULT_INPUTS_PATH,
                      out_dir: Path = EXAMPLES_DIR,
                      settings: OllamaSettings | None = None) -> list[Path]:
    """Generate every example, then write them all. Returns the written paths."""
    groups = load_groups(inputs_path)
    settings = settings or OllamaSettings.from_env()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rendered = []
    for number, (name, group) in enumerate(groups, start=1):
        print(f"Generating example {number} of {len(groups)} ({name})...", flush=True)
        result = generate_plan_result(group, settings)
        if result.fallback_reason:
            raise PlanError(f"example {number} ({name}) has no model sentence: "
                            f"{result.fallback_reason}")
        rendered.append(render_example(number, name, group, result, settings, generated_at))

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for number, text in enumerate(rendered, start=1):
        path = out_dir / f"example-{number}.md"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the saved group-plan examples.")
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS_PATH,
                        help=f"example groups (default: {DEFAULT_INPUTS_PATH})")
    parser.add_argument("--out", type=Path, default=EXAMPLES_DIR,
                        help=f"folder for example-N.md (default: {EXAMPLES_DIR})")
    args = parser.parse_args(argv)

    try:
        paths = generate_examples(args.inputs, args.out)
    except PlanError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"Error: could not write the examples: {err}", file=sys.stderr)
        return 1

    for path in paths:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
