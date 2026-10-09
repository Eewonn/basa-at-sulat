"""Smoke test for P0-AI-2: does the pinned stack still ship forced alignment + the MMS aligner?

Usage (from the repo root, venv active):
    python ai/smoke_test.py path/to/reading.wav "the passage text it reads"

Weights are cached in models/ (git-ignored).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("TORCH_HOME", str(ROOT / "models" / "torch"))

import re

import soundfile as sf
import torch
import torchaudio
import torchaudio.functional as F


def main(audio_path: str, text: str) -> None:
    print(f"torch {torch.__version__} / torchaudio {torchaudio.__version__}")
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model()
    model.eval()
    tokenizer, aligner = bundle.get_tokenizer(), bundle.get_aligner()

    data, sr = sf.read(audio_path, dtype="float32", always_2d=True)
    wav = torch.from_numpy(data.mean(axis=1)).unsqueeze(0)
    if sr != bundle.sample_rate:
        wav = F.resample(wav, sr, bundle.sample_rate)

    words = re.sub(r"[^a-z' ]", " ", text.lower()).split()
    with torch.inference_mode():
        emission, _ = model(wav)
    spans = aligner(emission[0], tokenizer(words))

    ratio = wav.shape[1] / emission.shape[1] / bundle.sample_rate
    for word, span in zip(words, spans):
        score = sum(s.score * len(s) for s in span) / sum(len(s) for s in span)
        print(f"{word:12s} {span[0].start * ratio:6.2f}-{span[-1].end * ratio:6.2f}s  score={score:.2f}")
    assert len(spans) == len(words)
    print("OK: MMS_FA + forced alignment work on this stack")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
