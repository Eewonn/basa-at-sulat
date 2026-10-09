"""The check_word evaluation's summary (no model, no recordings)."""

import check_word_eval


def test_summary_counts_match_rates_per_set_kind_and_recording():
    match, miss = {"result": "match", "score": 0.9}, {"result": "no_match", "score": 0.1}
    results = [
        ("tuning", "correct", "fil_001", "a.wav", "palay", match),
        ("tuning", "correct", "fil_001", "b.wav", "sa", miss),
        ("tuning", "swap", "fil_002", "c.wav", "palay", miss),
        ("confirmation", "silence", "fil_016", "d.wav", "Si", miss),
    ]
    text = check_word_eval.summarise(results, {"fil_001": "quiet"})
    assert "| tuning | correct | 2 | 1 (50%) |" in text
    assert "| tuning | swap | 1 | 0 (0%) |" in text
    assert "| confirmation | silence | 1 | 0 (0%) |" in text
    assert "- fil_001 (quiet): 1/2" in text
