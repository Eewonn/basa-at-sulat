"""Public interface of the ai package.

score() is real (MMS forced alignment, see aligner.py). word_timings() and check_word() are still STUBS
that return the docs/API.md shapes so the engine can wire against them (P2-AI-1 and P2-AI-2 replace them).
"""
import time
import wave

from . import aligner, text

# --- thresholds -------------------------------------------------------------
# UNTUNED starting values, picked by eye on clean synthetic speech. P1-AI-1 tunes them on eval/ recordings.
# Never tune on demo recordings.
MISREAD_BELOW = 0.6  # a word whose letters fit the audio worse than this is flagged
SKIP_BELOW = 0.5  # ...and if it was also squeezed into the fewest frames it could get, it's "skipped"
SQUEEZED_FRAMES_PER_CHAR = 1.25  # a word cramped to ~1 frame per letter had no real speech of its own
PAUSE_SEC = 1.0  # a gap between two words at least this long is reported as a hesitation


def label_word(mean_prob: float, n_chars: int, frames_per_char: float) -> str:
    """"matched" | "misread" | "skipped" from how well a word's letters fit the audio.

    A skipped word still has to be placed somewhere (the aligner needs a frame for every letter), so it
    ends up squeezed between its neighbours with no probability behind it. One-letter words are always
    one frame per letter, so they can't show the squeeze and are only ever "matched" or "misread".
    """
    if mean_prob >= MISREAD_BELOW:
        return "matched"
    if n_chars >= 2 and frames_per_char <= SQUEEZED_FRAMES_PER_CHAR and mean_prob < SKIP_BELOW:
        return "skipped"
    return "misread"


def score(audio_path: str, passage_text: str) -> dict:
    """Basa: label every passage word and report pauses.

    Returns {"words": [{"i", "text", "label", "score", "start", "end"}],
             "pauses": [{"before_word", "seconds"}],
             "timings": {"align_ms", "score_ms"}}
    `i` and `text` follow docs/API.md: the passage split on whitespace, punctuation attached.
    `score` is 0-1, how well the word's letters fit the audio (higher is better). `start`/`end` are seconds.
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
        mean_prob = sum(a.token_scores) / len(a.token_scores)
        frames_per_char = (a.end_frame - a.start_frame) / n
        start, end = round(a.start_frame * result.frame_sec, 2), round(a.end_frame * result.frame_sec, 2)
        if i > 0 and start - prev_end >= PAUSE_SEC:
            pauses.append({"before_word": i, "seconds": round(start - prev_end, 2)})
        rows.append({"i": i, "text": word, "label": label_word(mean_prob, n, frames_per_char),
                     "score": round(mean_prob, 2), "start": start, "end": end})
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
