"""Alignment and word scoring. A plain Python package: no web code.

The engine imports from here: `from ai import score`. Call `ai.warm_up()` once at startup.
"""
from .aligner import model_loaded, warm_up
from .scoring import check_word, score, word_timings

__all__ = ["score", "word_timings", "check_word", "warm_up", "model_loaded"]
