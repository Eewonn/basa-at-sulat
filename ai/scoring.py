"""Public interface of the ai package (P1-AI-1 skeleton).

These are STUBS: they return the shapes in docs/API.md so the engine can wire
against them now. Every word comes back "matched". The real MMS alignment and
scoring replace the bodies later, without changing the signatures.
"""
import wave

# Used when the file isn't a readable wav (the stub never needs real audio).
_FALLBACK_SEC_PER_WORD = 0.4
_STUB_SCORE = 0.9


def _words(text: str) -> list[str]:
    """Words as the contract indexes them: the passage split on whitespace.

    Punctuation stays attached ("bukid."), matching docs/api/assess.example.json.
    """
    return text.split()


def _duration(audio_path: str, n_words: int) -> float:
    try:
        with wave.open(audio_path, "rb") as f:
            return f.getnframes() / f.getframerate()
    except (wave.Error, EOFError, FileNotFoundError, OSError):
        return n_words * _FALLBACK_SEC_PER_WORD


def word_timings(audio_path: str, text: str) -> list[dict]:
    """Sulat: start/end seconds for each word of a fluent speaker's correct reading.

    Returns [{"i", "text", "start", "end"}]. Stub: words spread evenly over the audio.
    """
    words = _words(text)
    if not words:
        return []
    step = _duration(audio_path, len(words)) / len(words)
    return [
        {"i": i, "text": w, "start": round(i * step, 2), "end": round((i + 1) * step, 2)}
        for i, w in enumerate(words)
    ]


def score(audio_path: str, passage_text: str) -> dict:
    """Basa: label every passage word and report pauses.

    Returns {"words": [{"i", "text", "label", "score", "start", "end"}],
             "pauses": [{"before_word", "seconds"}]}
    with label one of "matched" | "misread" | "skipped" (see docs/API.md).
    Stub: everything is "matched" and there are no pauses.
    """
    words = [
        {**w, "label": "matched", "score": _STUB_SCORE}
        for w in word_timings(audio_path, passage_text)
    ]
    return {"words": words, "pauses": []}


def check_word(audio_path: str, word: str) -> dict:
    """Sanay "Say it": did the child say this one word?

    Returns {"result": "match" | "no_match", "score": 0-1}. Stub: always a match.
    """
    return {"result": "match", "score": _STUB_SCORE}
