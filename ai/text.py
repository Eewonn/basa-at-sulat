"""Turn passage words into what the MMS aligner can read.

The aligner's vocabulary is a-z and the apostrophe (plus `*`, "anything"). It has no n-tilde,
accents, digits or punctuation, and its token 0 is the CTC *blank*, which spells the hyphen: a
hyphen left in a word would put the blank into the target text and corrupt the alignment. So
"mag-aral" must become "magaral". Filipino spelling is close to its sound, which is why letter-level
alignment suits it.
"""
import unicodedata

VOCAB = frozenset("abcdefghijklmnopqrstuvwxyz'")
_APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'", "`": "'", "´": "'"}


def normalize_word(word: str) -> str:
    """Lowercase letters (and inner apostrophes) the aligner knows. May be empty, e.g. for "2026" or "—".

    - n-tilde becomes "ny" (Niño → "ninyo"), other accents are dropped (café → "cafe").
    - Hyphens and other punctuation are dropped; leading/trailing apostrophes are quote marks, so dropped.
      Inner apostrophes stay: they mark the glottal stop in Filipino (pa'no) and contractions in English.
    """
    w = word.lower()
    for fancy, plain in _APOSTROPHES.items():
        w = w.replace(fancy, plain)
    w = w.replace("ñ", "ny")  # before decomposing, or it would collapse to a plain "n"
    w = "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))
    w = "".join(c for c in w if c in VOCAB)
    return w.strip("'")


def split_words(text: str) -> list[str]:
    """Words as docs/API.md indexes them: split on whitespace, punctuation left attached."""
    return text.split()
