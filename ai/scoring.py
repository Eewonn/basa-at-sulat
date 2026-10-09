"""Public interface of the ai package.

score() is real (MMS forced alignment, see aligner.py). word_timings() and check_word() are still STUBS
that return the docs/API.md shapes so the engine can wire against them (P2-AI-1 and P2-AI-2 replace them).
"""
import math
import time
import wave

from . import aligner, text

# --- thresholds -------------------------------------------------------------
# Tuned on eval/: 15 Filipino readings of fil_g2_01 by one adult reader (2026-10-10). Never tune on demo
# recordings. See eval/README.md for how to re-run the test.
LOG_RANGE = 4  # word score = 1 + log10(weakest letter's probability) / 4, clipped to 0-1
FLAG_AT_OR_BELOW = 0.25  # = a letter with under a 1-in-1000 chance. F1 is flat (0.74-0.78) for 0.00-0.35;
#                          0.25 leans to recall, since the teacher confirms every flag and a miss goes unseen
SQUEEZED_FRAMES_PER_CHAR = 1.25  # a word cramped to ~1 frame per letter had no real speech of its own
PAUSE_SEC = 1.0  # a gap between two words at least this long is reported as a hesitation


def word_score(letter_probs: list) -> float:
    """0-1 from the word's WEAKEST letter, on a log scale (1.0 = every letter clearly there).

    Not the average: a near-miss swap (palay -> "pala", lolo -> "lola") gets every letter right but one,
    so the average stays high while that one letter's probability collapses. On the eval set, scoring
    the weakest letter raised held-out F1 from 0.55 to about 0.76. The log scale spreads out the tiny
    probabilities where the decision happens (1e-2 -> 0.5, 1e-3 -> 0.25, 1e-4 and below -> 0).
    """
    weakest = max(min(letter_probs), 1e-12)
    return max(0.0, min(1.0, 1 + math.log10(weakest) / LOG_RANGE))


def label_word(score: float, n_chars: int, frames_per_char: float) -> str:
    """"matched" | "misread" | "skipped" from the word score and how much time the word got.

    A skipped word still has to be placed somewhere (the aligner needs a frame for every letter), so it
    ends up squeezed between its neighbours. One-letter words are always one frame per letter, so they
    can't show the squeeze and are only ever "matched" or "misread".
    """
    if score > FLAG_AT_OR_BELOW:
        return "matched"
    if n_chars >= 2 and frames_per_char <= SQUEEZED_FRAMES_PER_CHAR:
        return "skipped"
    return "misread"


def score(audio_path: str, passage_text: str) -> dict:
    """Basa: label every passage word and report pauses.

    Returns {"words": [{"i", "text", "label", "score", "start", "end"}],
             "pauses": [{"before_word", "seconds"}],
             "timings": {"align_ms", "score_ms"}}
    `i` and `text` follow docs/API.md: the passage split on whitespace, punctuation attached.
    `score` is 0-1 from the word's weakest letter (higher is better; see word_score). `start`/`end` are seconds.
    `timings`: align_ms = reading the audio, running the model and aligning (nearly all the time, and it
    includes the ~10 s model load if warm_up() wasn't called); score_ms = turning that into labels and pauses.

    - Audio too short to hold the text: every word is "skipped" (nothing was read).
    - Words with no letters the aligner knows (digits, dashes) can't be checked: they come back "matched"
      with score 1.0 so they never raise a false alarm. Keep digits out of passages.
    - Raises if the audio file can't be read: convert to wav first (the engine's audio pipeline does).
    """
    started = time.perf_counter()
    words = text.split_words(passage_text)
    normalised = [text.normalize_word(w) for w in words]
    alignable = [i for i, n in enumerate(normalised) if n]

    result = None
    if alignable:
        result = aligner.align(audio_path, [normalised[i] for i in alignable])
    aligned = time.perf_counter()

    def timings():
        return {"align_ms": round((aligned - started) * 1000), "score_ms": round((time.perf_counter() - aligned) * 1000)}

    if not words:
        return {"words": [], "pauses": [], "timings": timings()}
    if alignable and result is None:  # too short for the text
        return {
            "words": [
                {"i": i, "text": w, "label": "skipped" if normalised[i] else "matched",
                 "score": 0.0 if normalised[i] else 1.0, "start": 0.0, "end": 0.0}
                for i, w in enumerate(words)
            ],
            "pauses": [],
            "timings": timings(),
        }
    by_index = dict(zip(alignable, result.words)) if result else {}

    rows, pauses, prev_end = [], [], 0.0
    for i, word in enumerate(words):
        a = by_index.get(i)
        if a is None:  # unalignable: sits at the previous word's end
            rows.append({"i": i, "text": word, "label": "matched", "score": 1.0, "start": prev_end, "end": prev_end})
            continue
        n = len(normalised[i])
        ws = word_score(a.token_scores)
        frames_per_char = (a.end_frame - a.start_frame) / n
        start, end = round(a.start_frame * result.frame_sec, 2), round(a.end_frame * result.frame_sec, 2)
        if i > 0 and start - prev_end >= PAUSE_SEC:
            pauses.append({"before_word": i, "seconds": round(start - prev_end, 2)})
        rows.append({"i": i, "text": word, "label": label_word(ws, n, frames_per_char),
                     "score": round(ws, 2), "start": start, "end": end})
        prev_end = end
    return {"words": rows, "pauses": pauses, "timings": timings()}


# --- stubs (P2-AI-1, P2-AI-2) -----------------------------------------------

_FALLBACK_SEC_PER_WORD = 0.4  # when the file isn't a readable wav
_STUB_SCORE = 0.9


def _duration(audio_path: str, n_words: int) -> float:
    try:
        with wave.open(audio_path, "rb") as f:
            return f.getnframes() / f.getframerate()
    except (wave.Error, EOFError, FileNotFoundError, OSError):
        return n_words * _FALLBACK_SEC_PER_WORD


def word_timings(audio_path: str, text_: str) -> list[dict]:
    """Sulat: start/end seconds for each word of a fluent speaker's correct reading.

    Returns [{"i", "text", "start", "end"}]. STUB: words spread evenly over the audio.
    """
    words = text.split_words(text_)
    if not words:
        return []
    step = _duration(audio_path, len(words)) / len(words)
    return [
        {"i": i, "text": w, "start": round(i * step, 2), "end": round((i + 1) * step, 2)}
        for i, w in enumerate(words)
    ]


def check_word(audio_path: str, word: str) -> dict:
    """Sanay "Say it": did the child say this one word?

    Returns {"result": "match" | "no_match", "score": 0-1}. STUB: always a match.
    """
    return {"result": "match", "score": _STUB_SCORE}
