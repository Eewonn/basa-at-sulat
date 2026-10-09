# ai/: alignment and word scoring

**Owner:** AI engineer · **Tasks:** P0-AI-*, P1-AI-*, P2-AI-*, P3-AI-* in [../docs/TASKS.md](../docs/TASKS.md)

## What lives here
A plain Python package the engine imports. No web code.

```python
score(audio_path: str, passage_text: str) -> dict
# -> {"words": [{"i", "text", "label", "score", "start", "end"}], "pauses": [{"before_word", "seconds"}]}
# label: "matched" | "misread" | "skipped"   (see ../docs/API.md)

word_timings(audio_path: str, text: str) -> list[dict]   # Sulat: a fluent speaker's correct reading
check_word(audio_path: str, word: str) -> dict           # Sanay "Say it": {"result": "match"|"no_match", "score"}
```

**Status:** the three functions are importable stubs (`from ai import score`). They return the contract shape with every word `matched`, so the engine can wire against them now. The real alignment replaces the bodies in P1-AI-1; the signatures won't change.

Run the interface tests from `ai/`: `python -m pytest`.

## Approach (to validate in P0-AI-1)
1. Normalize and romanize the passage (lowercase, uroman), keeping a map back to the original words.
2. Run Meta's MMS aligner (`torchaudio.pipelines.MMS_FA`, or the Hugging Face port) on 16 kHz mono audio, giving per-frame character probabilities.
3. Force-align to the known text, with a `<star>` token so extra speech doesn't break the alignment.
4. Score each word, e.g. the average log-probability of its aligned characters compared with the best free choice per frame (a goodness-of-pronunciation-style score), plus duration and the gap before the word.
5. Apply thresholds: misread / skipped / pause. Tune them on `eval/`, never on demo recordings.

**Fallback (P1-AI-2):** Whisper prompted with the passage, for Filipino and English only.

## Setup
```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r ai/requirements.txt
python ai/smoke_test.py path/to/reading.wav "the passage text it reads"
```
The first run downloads the MMS aligner (about 1.2 GB) into `models/torch/` (git-ignored).

## Rules
- Weights are downloaded by script into `models/` (git-ignored). Never commit them.
- Pin versions in `requirements.txt`.
- License: MMS is **CC-BY-NC-4.0**. Record every model and license for the README (P3-AI-2).
