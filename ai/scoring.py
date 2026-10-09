"""Public interface of the ai package.

score(), word_timings() and check_word() all use MMS forced alignment (see aligner.py).
"""
import math
import time

from . import aligner, text

# --- thresholds -------------------------------------------------------------
# Tuned on eval/: 15 Filipino readings of fil_g2_01 by one adult reader (2026-10-10). Never tune on demo
# recordings. See eval/README.md for how to re-run the test.
LOG_RANGE = 4  # word score = 1 + log10(weakest letter's probability) / 4, clipped to 0-1
FLAG_AT_OR_BELOW = 0.25  # = a letter with under a 1-in-1000 chance. F1 is flat (0.74-0.78) for 0.00-0.35;
#                          0.25 leans to recall, since the teacher confirms every flag and a miss goes unseen
SQUEEZED_FRAMES_PER_CHAR = 1.25  # a word cramped to ~1 frame per letter had no real speech of its own
PAUSE_SEC = 1.0  # a gap between two words at least this long is reported as a hesitation

# word_timings(): the aligner marks each letter with a short spike, so a word's raw span runs from its first
# letter's spike to its last and misses the start of the first sound and the tail of the last. Each word is
# widened by these pads, but never past the midpoint to its neighbour, so clips never overlap. Inside a
# sentence words nearly touch (median gap 0.06 s in our clean readings), so their clips meet at the midpoint;
# at a sentence break (up to 0.8 s) the silence is left out. Starting values: check by ear (P2-AI-1).
# check_word(): a word matches when its fit is less than this far (in total log-probability) below the model's
# own best guess. Chosen on clips from the tuning readings (best balanced accuracy at 8.93, rounded) and
# checked on clips from the confirmation readings; see eval/check_word_eval.py.
MATCH_GAP_LIMIT = 9.0
PAD_BEFORE_SEC = 0.10
PAD_AFTER_SEC = 0.15


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


def word_timings(audio_path: str, text_: str) -> list[dict]:
    """Sulat: start/end seconds for every word of a fluent speaker's correct reading.

    Returns [{"i", "text", "start", "end"}], `i` and `text` as in docs/API.md. Used to highlight each word
    as the story plays and to cut word clips for Sanay ("Hear it"). Each word's raw span is widened by
    PAD_BEFORE_SEC / PAD_AFTER_SEC, capped at the midpoint to its neighbours, so consecutive words never
    overlap and a word's clip holds the whole word without its neighbour.

    - Words with no letters the aligner knows (digits, dashes) get a zero-length time at the previous
      word's end. Keep digits out of stories.
    - Raises ValueError if the audio is too short to hold the text: that isn't a reading of this story.
    - Raises if the audio file can't be read: convert to wav first.
    """
    words = text.split_words(text_)
    normalised = [text.normalize_word(w) for w in words]
    alignable = [i for i, n in enumerate(normalised) if n]
    if not alignable:
        return [{"i": i, "text": w, "start": 0.0, "end": 0.0} for i, w in enumerate(words)]
    result = aligner.align(audio_path, [normalised[i] for i in alignable])
    if result is None:
        raise ValueError("the recording is too short to be a reading of this text")

    raw = [(a.start_frame * result.frame_sec, a.end_frame * result.frame_sec) for a in result.words]
    bounds = []
    for k, (start, end) in enumerate(raw):
        lo = (raw[k - 1][1] + start) / 2 if k > 0 else 0.0
        hi = (end + raw[k + 1][0]) / 2 if k + 1 < len(raw) else result.duration_sec
        bounds.append((max(start - PAD_BEFORE_SEC, lo), min(end + PAD_AFTER_SEC, hi)))
    by_index = dict(zip(alignable, bounds))

    out, prev_end = [], 0.0
    for i, word in enumerate(words):
        start, end = by_index.get(i, (prev_end, prev_end))
        out.append({"i": i, "text": word, "start": round(start, 2), "end": round(end, 2)})
        prev_end = end
    return out


def check_word(audio_path: str, word: str) -> dict:
    """Sanay "Say it": did the child say this word?

    Returns {"result": "match" | "no_match", "score": 0-1}, matching when score > 0.5.

    Not Basa's weakest-letter rule: a lone word isn't pinned between neighbours, so its letters can always
    find some frames that fit a little, and silence or a different word passed that rule 75-100% of the
    time. Instead, the fit to the word is compared with the model's own best guess (aligner.fit_gap):
    score = 1 + gap / (2 * MATCH_GAP_LIMIT), clipped to 0-1.

    On clips cut from the eval readings (eval/check_word_eval.py): correct words match 87-100% of the time
    except with TV or other people talking in the background (26%), other words are rejected about 80% of
    the time and silence is rejected, but a near-miss (bola -> "bula") still passes about 40% of the time.
    So it's encouragement for practice, not an assessment.

    - Several words ("mga bata") are checked together.
    - A word with no letters the aligner knows (digits, dashes) can't be checked: "match", score 1.0.
    - Nothing said (the model hears only silence) or audio too short to hold the word: "no_match", score 0.0.
    - Raises if the audio file can't be read: convert to wav first.
    """
    normalised = [n for n in (text.normalize_word(w) for w in text.split_words(word)) if n]
    if not normalised:
        return {"result": "match", "score": 1.0}
    fit = aligner.fit_gap(audio_path, normalised)
    if fit is None or fit.speech_frames == 0:  # too short, or nothing was said
        return {"result": "no_match", "score": 0.0}
    score = max(0.0, min(1.0, 1 + fit.gap / (2 * MATCH_GAP_LIMIT)))
    return {"result": "match" if score > 0.5 else "no_match", "score": round(score, 2)}
