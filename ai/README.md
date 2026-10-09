# ai/: alignment and word scoring

**Owner:** AI engineer · **Tasks:** P0-AI-*, P1-AI-*, P2-AI-*, P3-AI-* in [../docs/TASKS.md](../docs/TASKS.md)

## What lives here
A plain Python package the engine imports. No web code.

```python
score(audio_path: str, passage_text: str) -> dict
# -> {"words": [{"i", "text", "label", "score", "start", "end"}], "pauses": [{"before_word", "seconds"}],
#     "timings": {"align_ms", "score_ms"}}
# label: "matched" | "misread" | "skipped"   (see ../docs/API.md)
# align_ms: read audio + model + alignment (nearly all of it); score_ms: labels and pauses (milliseconds)

warm_up() -> None        # load the model (~10 s) at engine startup, so the first child's check isn't slow
model_loaded() -> bool   # for GET /health: "loaded" / "not_loaded"

word_timings(audio_path: str, text: str) -> list[dict]   # Sulat: a fluent speaker's correct reading
check_word(audio_path: str, word: str) -> dict           # Sanay "Say it": {"result": "match"|"no_match", "score"}
```

**Status:** `score()` is real (MMS forced alignment). `word_timings()` and `check_word()` are still stubs that return the contract shape (P2-AI-1, P2-AI-2). **The thresholds in `scoring.py` are untuned starting values**: P1-AI-1 isn't done until they're tuned on real recordings in `eval/`.

Run the tests from `ai/`: `python -m pytest`. The model-backed tests skip if the weights aren't downloaded.

## Approach (to validate in P0-AI-1)
1. `text.py` normalizes each passage word to what the aligner knows: lowercase `a-z` and the apostrophe. `ñ` becomes `ny`, accents and punctuation go, and **hyphens are removed** (token 0 is the CTC blank, so `mag-aral` would corrupt the alignment). The original word and its index are kept for the output.
2. `aligner.py` runs Meta's MMS aligner (`torchaudio.pipelines.MMS_FA`) on 16 kHz mono audio and force-aligns the known letters, with a `*` wildcard **only before and after the text** so chatter at either end doesn't land on the first or last word. Never between words: `*` costs nothing at any frame and would swallow real speech.
3. `scoring.py` turns each word into a score: the mean probability of its letters at their aligned frames (0 to 1), plus its frames per letter.
4. Labels: score ≥ 0.6 → `matched`; below that, `skipped` if the word was squeezed to about one frame per letter (the aligner still has to put every letter somewhere), otherwise `misread`. A gap of 1 s or more before a word is a pause.
5. Tune the cutoffs on `eval/`, never on demo recordings.

**Known limits**
- A swap to a similar-sounding word that shares letters (kite → bike) scores middling and is the hardest case.
- Words with no aligner letters (digits, dashes) can't be checked and come back `matched`. Keep digits out of passages.
- Audio too short to hold the text comes back all `skipped`.
- Speed: about 6.5 s to score 10.5 s of audio on an 8-core CPU laptop (after a one-time ~10 s model load), roughly 0.6× real time.
- `torchaudio.functional.forced_align` is deprecated and **removed in torchaudio 2.9**, so `requirements.txt` stays on 2.8.x. If we ever need to move, the replacements are the standalone `ctc-forced-aligner` package or our own CTC alignment over the Hugging Face MMS model.

**Fallback (P1-AI-2):** Whisper prompted with the passage, for Filipino and English only.

## Setup
```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r ai/requirements.txt       # to run the scorer (the engine needs this too)
pip install -r ai/requirements-dev.txt   # ...plus pytest, to run the ai/ and eval/ tests
python ai/smoke_test.py path/to/reading.wav "the passage text it reads"
```
The first run downloads the MMS aligner (about 1.2 GB) into `models/torch/` (git-ignored).
The `eval/` tests run in this same environment: they import `ai` and need `soundfile`, which `engine/requirements.txt` doesn't install.

## Rules
- Weights are downloaded by script into `models/` (git-ignored). Never commit them.
- Pin versions in `requirements.txt`.
- License: MMS is **CC-BY-NC-4.0**. Record every model and license for the README (P3-AI-2).
