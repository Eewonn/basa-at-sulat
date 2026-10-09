"""Alignment and word scoring. A plain Python package: no web code.

The engine imports from here: `from ai import score`.
"""
from .scoring import check_word, score, word_timings

__all__ = ["score", "word_timings", "check_word"]
