"""Sanay practice sets: a learner's missed words from their latest check (P2-BE2-1).

Contract: docs/API.md, `GET /learners/{id}/practice`. Each item is a missed
word, the passage sentence it came from, and a clip reference into a Sulat
book's model reading (`book_id`, `word_index`), or null for both when no book
holds the word.

Passages and books aren't linked in the schema, so a clip is found by the
word's text: the first timed occurrence of the same word in a book of the
same language. Words are compared with ai.text.normalize_word, the rule the
aligner uses, so "Palay," and "palay" find the same clip.
"""

import sqlite3

from ai.text import normalize_word
from app.plans import PUNCTUATION

MISSED_LABELS = ("misread", "skipped")
# Closing quotes and brackets can follow a full stop: «"Tara na!" sabi niya.»
SENTENCE_ENDS = (".", "!", "?", "…")
TRAILING_CLOSERS = "\"'”’)]»"
OPENERS = "\"'“‘([«"


class LearnerNotFoundError(Exception):
    """No learner with the given id."""


def _ends_sentence(tokens: list[str], i: int) -> bool:
    """Word i closes a sentence: it ends in . ! ? or …, and the next word doesn't start in lowercase.

    The second rule keeps dialogue together: in «"Tara na!" sabi niya.» the
    "!" is followed by "sabi", so the child rereads the whole line.
    """
    if not tokens[i].rstrip(TRAILING_CLOSERS).endswith(SENTENCE_ENDS):
        return False
    if i == len(tokens) - 1:
        return True
    following = tokens[i + 1].lstrip(OPENERS)
    return not following[:1].islower()


def sentence_at(tokens: list[str], i: int) -> str:
    """The sentence holding word i, rebuilt from the passage's whitespace-split words.

    Found by index, not by searching for the text, so a word that appears in
    two sentences gets the one it was actually missed in.
    """
    start = i
    while start > 0 and not _ends_sentence(tokens, start - 1):
        start -= 1
    end = i
    # A passage whose last sentence has no full stop still ends at its last word.
    while end < len(tokens) - 1 and not _ends_sentence(tokens, end):
        end += 1
    return " ".join(tokens[start:end + 1])


def _latest_confirmed_check(conn: sqlite3.Connection, learner_id: str):
    # created_at breaks ties, so two checks confirmed in the same millisecond still have an order.
    return conn.execute(
        "SELECT a.id, p.text, p.language FROM assessments a "
        "JOIN passages p ON p.id = a.passage_id "
        "WHERE a.learner_id = ? AND a.status = 'confirmed' "
        "ORDER BY a.confirmed_at DESC, a.created_at DESC, a.id DESC LIMIT 1",
        (learner_id,),
    ).fetchone()


def _clip_index(conn: sqlite3.Connection, language: str) -> dict[str, tuple[str, int]]:
    """Map each normalized word to its first usable clip in this language's books.

    The oldest book wins, then the earliest word in it, so a word's clip stays
    the same when newer books are added. Words with zero-length timings
    (digits, dashes) have no audio to cut, so they are skipped.
    """
    clips: dict[str, tuple[str, int]] = {}
    rows = conn.execute(
        "SELECT w.book_id, w.i, w.text FROM book_words w "
        "JOIN books b ON b.id = w.book_id "
        "WHERE b.language = ? AND w.end_sec > w.start_sec "
        "ORDER BY b.created_at, b.id, w.i",
        (language,),
    )
    for row in rows:
        key = normalize_word(row["text"])
        if key and key not in clips:
            clips[key] = (row["book_id"], row["i"])
    return clips


def build_practice_set(conn: sqlite3.Connection, learner_id: str) -> list[dict]:
    """Return the practice items for a learner, in passage order.

    Missed means the teacher's final label is misread or skipped, so an
    override counts both ways. Repeats of a word appear once, with the
    sentence of its first miss. A learner with no confirmed check gets an
    empty list: drafts may still change, so they aren't practised.
    """
    if conn.execute("SELECT 1 FROM learners WHERE id = ?", (learner_id,)).fetchone() is None:
        raise LearnerNotFoundError(f"no learner '{learner_id}'")

    check = _latest_confirmed_check(conn, learner_id)
    if check is None:
        return []

    tokens = check["text"].split()
    missed = conn.execute(
        "SELECT i FROM word_results WHERE assessment_id = ? AND final_label IN (?, ?) ORDER BY i",
        (check["id"], *MISSED_LABELS),
    ).fetchall()
    clips = _clip_index(conn, check["language"]) if missed else {}

    items, seen = [], set()
    for row in missed:
        token = tokens[row["i"]]
        word = token.strip(PUNCTUATION)
        if not word:
            continue  # a stray dash or quote mark isn't something to practise
        # normalize_word is empty for words with no letters (e.g. "2026"); fall back to the word itself.
        key = normalize_word(token) or word.casefold()
        if key in seen:
            continue
        seen.add(key)
        book_id, word_index = clips.get(key, (None, None))
        items.append({
            "word": word,
            "sentence": sentence_at(tokens, row["i"]),
            "book_id": book_id,
            "word_index": word_index,
        })
    return items
