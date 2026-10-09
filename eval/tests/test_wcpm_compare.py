"""WCPM versus a human scorer, on hand-worked numbers (no model, no audio)."""

import json

import metrics
import wcpm_compare

HUMAN_HEADER = "recording_id,passage_id,passage_words,reading_seconds,words_correct,notes\n"
GT_HEADER = "recording_id,language,passage_id,word_index,expected,actual,error_type,reader,notes\n"


def setup(tmp_path, human_rows):
    # a 10-word passage, read from 1.0 s to 10.0 s of a 12 s recording; the app flags words 3 and 7,
    # but only word 3 was really misread
    words = [{"i": i, "text": f"w{i}", "label": "misread" if i in (3, 7) else "matched", "score": 0.9,
              "start": 1.0 + 0.9 * i, "end": 1.0 + 0.9 * (i + 1)} for i in range(10)]
    pred = tmp_path / "pred.json"
    pred.write_text(json.dumps({"predictions": {"fil_001": {"language": "fil", "passage_id": "p1", "duration_sec": 12.0,
                                                            "elapsed_sec": 1.0, "words": words, "pauses": []}},
                                "skipped": []}), encoding="utf-8")
    gt = tmp_path / "gt.csv"
    gt.write_text(GT_HEADER + "fil_001,fil,p1,3,w3,x,swap,KM,\n", encoding="utf-8")
    human = tmp_path / "human.csv"
    human.write_text(HUMAN_HEADER + "".join(r + "\n" for r in human_rows), encoding="utf-8")
    return human, pred, gt


def test_worked_example(tmp_path):
    human, pred, gt = setup(tmp_path, ["fil_001,p1,10,9.0,9,"])  # person: 9 correct in 9.0 s = 60 WCPM
    results = wcpm_compare.compare(wcpm_compare.load_human(human),
                                   json.loads(pred.read_text())["predictions"], metrics.load_ground_truth(gt))
    (r,) = results
    assert r["human_wcpm"] == 60
    assert r["app"]["draft"]["wcpm"] == 40  # 8 matched over the whole 12 s
    assert r["app"]["confirmed"]["wcpm"] == 45  # 9 correct over 12 s: the gap left is timing
    assert r["app"]["confirmed, read time"]["wcpm"] == 60  # 9 correct over 1.0-10.0 s
    s = wcpm_compare.summary(results)
    assert (s["draft"]["bias"], s["confirmed"]["bias"], s["confirmed, read time"]["mae"]) == (-20, -15, 0)
    assert s["confirmed, read time"]["same_level"] == 1


def test_unfilled_rows_are_ignored(tmp_path):
    human, _, _ = setup(tmp_path, ["fil_001,p1,10,,,", "fil_002,p1,10,9.5,,"])
    assert wcpm_compare.load_human(human) == []


def test_main_writes_the_report(tmp_path):
    human, pred, gt = setup(tmp_path, ["fil_001,p1,10,9.0,9,"])
    out = tmp_path / "WCPM.md"
    assert wcpm_compare.main(["--human", str(human), "--predictions", str(pred), "--ground-truth", str(gt),
                              "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "| draft | 20.0 | -20.0 | 33% |" in text
    assert "| fil_001 | 60 (" in text


def test_main_explains_missing_scores_and_empty_form(tmp_path, capsys):
    human, pred, gt = setup(tmp_path, ["fil_001,p1,10,9.0,9,"])
    assert wcpm_compare.main(["--human", str(human), "--predictions", str(tmp_path / "nope.json"),
                              "--ground-truth", str(gt)]) == 1
    assert "run eval/run_eval.py first" in capsys.readouterr().out
    empty, _, _ = setup(tmp_path, ["fil_001,p1,10,,,"])
    assert wcpm_compare.main(["--human", str(empty), "--predictions", str(pred), "--ground-truth", str(gt)]) == 1
    assert "no filled rows" in capsys.readouterr().out
