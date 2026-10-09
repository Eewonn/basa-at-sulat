"""Sulat books: a story plus a fluent speaker's model reading (P2-BE1-1)."""

import logging
import re
import sqlite3
import uuid
import wave

from fastapi.responses import FileResponse, Response
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from ai import word_timings
from app.audio import AudioConversionError, convert_to_wav16k, cut_wav, storage_dir, stored_wav
from app.plans import PlanError
from app.routes.assessments import get_conn
from app.story import draft_story

log = logging.getLogger("engine.books")
router = APIRouter(prefix="/books", tags=["books"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_WORDS = 3000
# ISO 639 codes (fil, eng, ilo...), the same rule as the seed data.
LANGUAGE_PATTERN = re.compile(r"[a-z]{2,3}")


@router.post("")
def create_book(
    title: str = Form(...),
    language: str = Form(...),
    text: str = Form(...),
    audio: UploadFile = File(...),
    conn=Depends(get_conn),
):
    if not title.strip():
        raise HTTPException(422, "title can't be blank")
    if not LANGUAGE_PATTERN.fullmatch(language):
        raise HTTPException(422, "language must be a 2-3 letter lowercase code such as fil, eng or ilo")
    if not text.strip():
        raise HTTPException(422, "text can't be blank")
    if len(text.split()) > MAX_WORDS:
        raise HTTPException(422, f"the story is over {MAX_WORDS} words")

    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, f"the audio is over {MAX_AUDIO_BYTES // (1024 * 1024)} MB")

    book_id = f"b_{uuid.uuid4().hex[:8]}"
    books_dir = storage_dir() / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    upload_path = books_dir / f"{book_id}.upload"
    wav_path = books_dir / f"{book_id}.wav"
    try:
        upload_path.write_bytes(data)
        try:
            convert_to_wav16k(upload_path, wav_path)
        except AudioConversionError as err:
            raise HTTPException(400, f"could not read the audio: {err}") from err
        words = _time_the_words(wav_path, text, book_id)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO books (id, title, language, text, audio_path) VALUES (?, ?, ?, ?, ?)",
                    (book_id, title, language, text, f"books/{book_id}.wav"),
                )
                conn.executemany(
                    "INSERT INTO book_words (book_id, i, text, start_sec, end_sec) VALUES (?, ?, ?, ?, ?)",
                    [(book_id, w["i"], w["text"], w["start"], w["end"]) for w in words],
                )
        except sqlite3.Error as err:
            log.exception("could not save book %s", book_id)
            raise HTTPException(500, "could not save the book") from err
    except Exception:
        wav_path.unlink(missing_ok=True)  # nothing is kept when the book isn't saved
        raise
    finally:
        upload_path.unlink(missing_ok=True)
    return {"id": book_id, "words": words}


@router.post("/draft")
def draft_book_story(topic: str = Body(...), language: str = Body(...), idea: str = Body("")):
    """A short story the teacher can edit before recording it. Drafted by the local model; nothing is saved."""
    try:
        return draft_story(topic, language, idea)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    except PlanError as err:
        log.warning("story draft failed: %s", err)
        raise HTTPException(503, str(err)) from err


def _time_the_words(wav_path, text: str, book_id: str) -> list[dict]:
    try:
        return word_timings(str(wav_path), text)
    except ValueError as err:
        raise HTTPException(422, f"the audio doesn't fit the story: {err}") from err
    except ImportError as err:
        log.error("scoring model is not installed: %s", err)
        raise HTTPException(503, "the scoring model is not installed on this engine") from err
    except Exception as err:
        log.exception("word timing failed for %s", book_id)
        raise HTTPException(500, "could not time the words") from err


@router.get("")
def list_books(conn=Depends(get_conn)):
    """Every book, newest first, without word timings (GET /books/{id} has those)."""
    rows = conn.execute("SELECT id, title, language, text FROM books ORDER BY created_at DESC, id").fetchall()
    return [dict(r) for r in rows]


def _get_book(conn, book_id: str):
    book = conn.execute(
        "SELECT id, title, language, text, audio_path FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if book is None:
        raise HTTPException(404, f"no book '{book_id}'")
    return book


@router.get("/{book_id}")
def get_book(book_id: str, conn=Depends(get_conn)):
    book = _get_book(conn, book_id)
    words = conn.execute(
        "SELECT i, text, start_sec, end_sec FROM book_words WHERE book_id = ? ORDER BY i", (book_id,)
    ).fetchall()
    return {
        "id": book["id"],
        "title": book["title"],
        "language": book["language"],
        "text": book["text"],
        "words": [
            {"i": w["i"], "text": w["text"], "start": w["start_sec"], "end": w["end_sec"]} for w in words
        ],
    }


def _book_wav_path(book):
    """The book's stored WAV, or a 404 if it is missing or points outside the storage folder."""
    # The stored path must stay inside the storage folder, whatever the database holds.
    path = stored_wav(book["audio_path"])
    if path is None:
        raise HTTPException(404, f"the audio for book '{book['id']}' is missing")
    return path


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: str, conn=Depends(get_conn)):
    """Delete a book, its word timings and its model reading.

    Sanay attempts that played a clip from it are history, so they're kept: they just lose the clip reference.
    """
    book = _get_book(conn, book_id)
    with conn:
        conn.execute("UPDATE practice_attempts SET book_id = NULL, word_index = NULL WHERE book_id = ?", (book_id,))
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    path = stored_wav(book["audio_path"])
    if path is not None:
        path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.get("/{book_id}/audio")
def get_book_audio(book_id: str, conn=Depends(get_conn)):
    book = _get_book(conn, book_id)
    return FileResponse(_book_wav_path(book), media_type="audio/wav")


@router.get("/{book_id}/clips/{i}")
def get_word_clip(book_id: str, i: int, conn=Depends(get_conn)):
    """Word `i`'s audio, cut from the stored model reading. Nothing is written to disk."""
    book = _get_book(conn, book_id)
    word = conn.execute(
        "SELECT start_sec, end_sec FROM book_words WHERE book_id = ? AND i = ?", (book_id, i)
    ).fetchone()
    if word is None:
        raise HTTPException(404, f"book '{book_id}' has no word {i}")
    path = _book_wav_path(book)
    try:
        clip = cut_wav(path, word["start_sec"], word["end_sec"])  # a word can't run past the file
    except ValueError:
        raise HTTPException(422, f"word {i} has no audio in this reading") from None
    except (wave.Error, EOFError) as err:
        log.error("could not read the audio of %s: %s", book_id, err)
        raise HTTPException(404, f"the audio for book '{book_id}' is missing") from err
    return Response(clip, media_type="audio/wav")
