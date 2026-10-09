"""Download every model once, so the app can run offline afterwards.

    python scripts/download_models.py          # download what is missing
    python scripts/download_models.py --check  # only report; exit 1 if something is missing

Models: the MMS aligner (about 1.2 GB, needs torch from ai/requirements.txt) and the Ollama model the
group plans use. Ollama is optional: if it isn't installed we say so and carry on, because plans fall
back to templates. Anything already downloaded is skipped.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in (REPO_ROOT, REPO_ROOT / "engine"):  # `ai` lives at the repo root, `app` under engine/
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

PRESENT, MISSING, UNAVAILABLE = "present", "missing", "unavailable"


def ollama_status(model: str, run=subprocess.run) -> str:
    """present / missing, or unavailable when Ollama isn't installed or its server isn't running."""
    try:
        result = run(["ollama", "list"], capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return UNAVAILABLE
    if result.returncode != 0:
        return UNAVAILABLE
    names = [line.split()[0] for line in result.stdout.splitlines()[1:] if line.split()]
    return PRESENT if model in names else MISSING


def ollama_pull(model: str, run=subprocess.run) -> None:
    result = run(["ollama", "pull", model], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ollama pull {model} failed")


class Aligner:
    name = "MMS aligner (about 1.2 GB)"

    def status(self) -> str:
        from ai import aligner

        return PRESENT if aligner.weights_cached() else MISSING

    def download(self) -> None:
        from ai import aligner

        aligner.warm_up()  # downloads the weights into models/torch/ when they aren't cached


class Ollama:
    def __init__(self) -> None:
        from app.plans import OllamaSettings

        self.model = OllamaSettings.from_env().model
        self.name = f"Ollama model {self.model}"

    def status(self) -> str:
        return ollama_status(self.model)

    def download(self) -> None:
        ollama_pull(self.model)


def main(argv: list[str] | None = None, models=None) -> int:
    parser = argparse.ArgumentParser(description="Download the models Basa at Sulat needs, once.")
    parser.add_argument("--check", action="store_true", help="only report what is missing; download nothing")
    args = parser.parse_args(argv)
    models = [Aligner(), Ollama()] if models is None else models

    failed = missing = 0
    for model in models:
        status = model.status()
        if status == PRESENT:
            print(f"{model.name}: already downloaded")
        elif status == UNAVAILABLE:
            print(
                f"{model.name}: skipped. Ollama isn't installed or isn't running. Install it from ollama.com "
                "and start it; group plans use templates until then."
            )
        elif args.check:
            print(f"{model.name}: missing")
            missing += 1
        else:
            print(f"{model.name}: downloading...")
            try:
                model.download()
            except ImportError as err:
                print(f"{model.name}: FAILED ({err}). Install the AI packages first: pip install -r ai/requirements.txt")
                failed += 1
            except Exception as err:
                print(f"{model.name}: FAILED ({err})")
                failed += 1
            else:
                print(f"{model.name}: done")
    return 1 if failed or missing else 0


if __name__ == "__main__":
    sys.exit(main())
