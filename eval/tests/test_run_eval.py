"""The runner end to end: files in, REPORT.md out (P0-AI-1)."""

import json
import struct
import wave

import metrics
import run_eval

HEADER = "recording_id,language,passage_id,word_index,expected,actual,error_type,reader,notes\n"
PASSAGE = "one two three four five"
ROWS = [
    "fil_001,fil,p1,1,two,too,swap,KM,",
    "fil_001,fil,p1,3,four,,skip,KM,",
    "fil_002,fil,p1,,,,none,KM,",
    "fil_003,fil,p1,2,three,,skip,KM,",
    "fil_004,fil,p1,,,,none,KM,",
]


def make_wav(path, seconds=1.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack("<h", 0) * int(16000 * seconds))


def project(tmp_path, have_audio=("fil_001", "fil_002", "fil_003", "fil_004")):
    gt = tmp_path / "ground_truth.csv"
    gt.write_text(HEADER + "".join(r + "\n" for r in ROWS), encoding="utf-8")
    passages = tmp_path / "passages.json"
    passages.write_text(json.dumps([{"id": "p1", "language": "fil", "text": PASSAGE}]), encoding="utf-8")
    for rec_id in have_audio:
        make_wav(tmp_path / "recordings" / "fil" / f"{rec_id}.wav")
    return gt, passages, tmp_path / "recordings"


def oracle_scorer(recordings):
    """A perfect scorer: low score exactly on the planted mistakes."""
    gold = {"fil_001": {1, 3}, "fil_003": {2}}
    current = {}

    def score(audio_path, text):
        rec_id = audio_path.replace("\\", "/").rsplit("/", 1)[1][:-4]
        words = []
        for i, w in enumerate(text.split()):
            bad = i in gold.get(rec_id, set())
            words.append({"i": i, "text": w, "label": "misread" if bad else "matched", "score": 0.1 if bad else 0.9,
                          "start": 0, "end": 0})
        return {"words": words, "pauses": []}

    return score


def test_evaluate_scores_each_recording_with_audio(tmp_path):
    gt, passages, recs_dir = project(tmp_path)
    preds, skipped = run_eval.evaluate(
        metrics.load_ground_truth(gt), run_eval.load_passages(passages), recs_dir, oracle_scorer(recs_dir), log=lambda *_: None
    )
    assert sorted(preds) == ["fil_001", "fil_002", "fil_003", "fil_004"]
    assert skipped == []
    assert preds["fil_001"]["duration_sec"] == 1.0
    assert len(preds["fil_001"]["words"]) == 5


def test_recordings_without_audio_are_skipped_and_reported(tmp_path):
    gt, passages, recs_dir = project(tmp_path, have_audio=("fil_001",))
    recs = metrics.load_ground_truth(gt)
    preds, skipped = run_eval.evaluate(recs, run_eval.load_passages(passages), recs_dir, oracle_scorer(recs_dir), log=lambda *_: None)
    assert list(preds) == ["fil_001"]
    assert sorted(r for r, _ in skipped) == ["fil_002", "fil_003", "fil_004"]
    assert "fil_002" in run_eval.build_report(recs, preds, skipped)


def test_a_perfect_scorer_gets_a_go_verdict(tmp_path):
    gt, passages, recs_dir = project(tmp_path)
    recs = metrics.load_ground_truth(gt)
    preds, skipped = run_eval.evaluate(recs, run_eval.load_passages(passages), recs_dir, oracle_scorer(recs_dir), log=lambda *_: None)
    report = run_eval.build_report(recs, preds, skipped)
    assert "**Overall: GO**" in report
    assert "| fil | labels from `score()` | 1.00 | 1.00 | 1.00 |" in report
    assert "swap | skip" in report


def matched_scorer(audio_path, text):
    """Like the old ai.score stub: every word matched, nothing flagged. Never loads the model."""
    return {"words": [{"i": i, "text": w, "label": "matched", "score": 0.9, "start": 0, "end": 0}
                      for i, w in enumerate(text.split())], "pauses": []}


def test_main_with_a_scorer_that_flags_nothing_is_no_go(tmp_path):
    """A scorer that marks every word matched catches no mistakes, so it must never produce a GO."""
    gt, passages, recs_dir = project(tmp_path)
    out = tmp_path / "REPORT.md"
    code = run_eval.main([
        "--ground-truth", str(gt), "--passages", str(passages), "--recordings", str(recs_dir),
        "--predictions", str(tmp_path / "out" / "predictions.json"), "--out", str(out),
    ], scorer=matched_scorer)
    assert code == 0
    assert "**Overall: NO-GO**" in out.read_text(encoding="utf-8")
    assert (tmp_path / "out" / "predictions.json").exists()


def test_reuse_rebuilds_the_report_without_running_the_model(tmp_path):
    gt, passages, recs_dir = project(tmp_path)
    args = ["--ground-truth", str(gt), "--passages", str(passages), "--recordings", str(recs_dir),
            "--predictions", str(tmp_path / "p.json")]
    run_eval.main(args + ["--out", str(tmp_path / "first.md")], scorer=matched_scorer)
    for wav in (recs_dir / "fil").glob("*.wav"):
        wav.unlink()  # prove --reuse doesn't need the audio
    assert run_eval.main(args + ["--out", str(tmp_path / "second.md"), "--reuse"]) == 0
    assert (tmp_path / "first.md").read_text(encoding="utf-8") == (tmp_path / "second.md").read_text(encoding="utf-8")


def test_empty_ground_truth_exits_with_a_hint(tmp_path, capsys):
    gt = tmp_path / "ground_truth.csv"
    gt.write_text(HEADER, encoding="utf-8")
    assert run_eval.main(["--ground-truth", str(gt)]) == 1
    assert "Record the test set" in capsys.readouterr().out


def test_main_defaults_to_ai_score_and_warms_the_model_up_first(tmp_path, monkeypatch):
    """Without a scorer, main() uses ai.score, after ai.warm_up() (so timing excludes the model load).

    Both are replaced here, so the model is never loaded and torch isn't needed.
    """
    import sys

    sys.path.insert(0, str(run_eval.ROOT))
    import ai

    calls = []
    monkeypatch.setattr(ai, "warm_up", lambda: calls.append("warm_up"))
    monkeypatch.setattr(ai, "score", lambda path, text: calls.append("score") or matched_scorer(path, text))
    gt, passages, recs_dir = project(tmp_path)
    run_eval.main(["--ground-truth", str(gt), "--passages", str(passages), "--recordings", str(recs_dir),
                   "--predictions", str(tmp_path / "p.json"), "--out", str(tmp_path / "r.md")])
    assert calls[0] == "warm_up" and calls.count("warm_up") == 1
    assert calls.count("score") == 4
