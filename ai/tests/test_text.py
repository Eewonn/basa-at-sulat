"""Passage normalisation for the MMS aligner (no model needed)."""

import pytest

from ai import text


@pytest.mark.parametrize(
    "word, expected",
    [
        ("Nagtanim", "nagtanim"),
        ("bukid.", "bukid"),
        ("strong,", "strong"),
        ("mag-aral", "magaral"),  # a hyphen would be the CTC blank token
        ("Niño", "ninyo"),
        ("NIÑA", "ninya"),
        ("café", "cafe"),
        ("pa'no", "pa'no"),  # glottal stop: inner apostrophe stays
        ("Ben's", "ben's"),
        ("'hello'", "hello"),  # quote marks are not part of the word
        ("don’t", "don't"),  # curly apostrophe
        ("2026", ""),
        ("—", ""),
        ("", ""),
    ],
)
def test_normalize_word(word, expected):
    assert text.normalize_word(word) == expected


def test_normalised_words_only_use_the_aligners_vocabulary():
    for w in ["Ñandú", "mag-uusap", "ika-5", "Ángel", "ng", "mga"]:
        assert set(text.normalize_word(w)) <= text.VOCAB


def test_split_words_keeps_punctuation_attached():
    assert text.split_words("Nagtanim si Lina ng palay sa bukid. Masaya siya.") == [
        "Nagtanim", "si", "Lina", "ng", "palay", "sa", "bukid.", "Masaya", "siya.",
    ]
    assert text.split_words("  a \n b  ") == ["a", "b"]
