"""How well does ai.check_word() (Sanay "Say it") tell a said word from something else? (P2-AI-2)

    python eval/check_word_eval.py

There are no real single-word recordings yet, so clips are cut from the eval readings with ai.word_timings()
and padded with half a second of the same recording's room noise on each side:
  - correct: every word of each clean reading          -> should match
  - swap:    each planted swap, cut where it was said   -> should not match
  - other:   a clip of one word checked against another -> should not match
  - silence: room noise only, against 3 target words   -> should not match
Results are shown separately for the tuning readings (MATCH_GAP_LIMIT was chosen on these) and the
confirmation readings (never tuned on). Clips cut from connected reading carry a little of their
neighbours, so a child saying one word on its own may fare better than this.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import metrics  # noqa: E402

KINDS = ("correct", "swap", "other", "silence")


def build_clips(sets: dict, passages: dict, recordings_dir: Path, out: Path, timer, seed: int = 7) -> list:
    """[(set, kind, recording_id, clip_path, target_word)] for every clean reading's words, the swaps,
    10 other-word pairs per clean reading, and a silence clip per set checked against its passage's first,
    shortest and longest word (short words are the hard case for silence)."""
    import numpy as np
    import soundfile as sf

    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for set_name, recs in sets.items():
        for rid, rec in sorted(recs.items()):
            wav = Path(recordings_dir) / rec.language / f"{rid}.wav"
            if not wav.exists():
                continue
            audio, sr = sf.read(str(wav), dtype="float32")
            room = audio[: int(0.5 * sr)]  # before the reading starts

            def cut(t):
                path = out / f"{rid}_{t['i']:02d}.wav"
                sf.write(str(path), np.concatenate([room, audio[int(t["start"] * sr): int(t["end"] * sr)], room]), sr)
                return str(path)

            timings = timer(str(wav), passages[rec.passage_id])
            if rec.clean:
                items += [(set_name, "correct", rid, cut(t), t["text"]) for t in timings]
                for _ in range(10):
                    a, b = rng.sample(timings, 2)
                    if a["text"].lower().strip(".,") != b["text"].lower().strip(".,"):
                        items.append((set_name, "other", rid, cut(a), b["text"]))
            items += [(set_name, "swap", rid, cut(timings[i]), timings[i]["text"])
                      for i, kind in sorted(rec.errors.items()) if kind == "swap"]
        first = next((r for r in sorted(recs.values(), key=lambda r: r.id)
                      if (Path(recordings_dir) / r.language / f"{r.id}.wav").exists()), None)
        if first:
            audio, sr = sf.read(str(Path(recordings_dir) / first.language / f"{first.id}.wav"), dtype="float32")
            path = out / f"silence_{set_name}.wav"
            sf.write(str(path), audio[: int(1.0 * sr)], sr)
            words = passages[first.passage_id].split()
            for target in dict.fromkeys([words[0], min(words, key=len), max(words, key=len)]):
                items.append((set_name, "silence", first.id, str(path), target))
    return items


def summarise(results: list, notes: dict) -> str:
    """Match rate per set and kind, and per recording for correct words. `results` rows end with check_word's dict."""
    lines = ["| Set | Kind | Clips | Matched |", "|---|---|---|---|"]
    for set_name in dict.fromkeys(r[0] for r in results):
        for kind in KINDS:
            rows = [r for r in results if r[0] == set_name and r[1] == kind]
            if rows:
                hit = sum(r[5]["result"] == "match" for r in rows)
                lines.append(f"| {set_name} | {kind} | {len(rows)} | {hit} ({hit / len(rows):.0%}) |")
    lines += ["", "Correct words matched, per recording:", ""]
    for rid in dict.fromkeys(r[2] for r in results if r[1] == "correct"):
        rows = [r for r in results if r[1] == "correct" and r[2] == rid]
        hit = sum(r[5]["result"] == "match" for r in rows)
        lines.append(f"- {rid} ({notes.get(rid, '')}): {hit}/{len(rows)}")
    return "\n".join(lines)


def main(argv=None, checker=None, timer=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recordings", default=HERE / "recordings")
    ap.add_argument("--passages", default=ROOT / "data" / "passages" / "passages.json")
    ap.add_argument("--clips", default=HERE / "out" / "check_word_clips")
    args = ap.parse_args(argv)
    if checker is None or timer is None:
        sys.path.insert(0, str(ROOT))
        import ai

        ai.warm_up()
        checker, timer = checker or ai.check_word, timer or ai.word_timings

    sets = {"tuning": metrics.load_ground_truth(HERE / "ground_truth.csv"),
            "confirmation": metrics.load_ground_truth(HERE / "confirm_ground_truth.csv")}
    passages = {p["id"]: p["text"] for p in json.loads(Path(args.passages).read_text(encoding="utf-8"))}
    notes = {}
    import csv

    for name in ("ground_truth.csv", "confirm_ground_truth.csv"):
        with open(HERE / name, newline="", encoding="utf-8") as f:
            notes.update({row["recording_id"]: row["notes"] for row in csv.DictReader(f)})
    items = build_clips(sets, passages, Path(args.recordings), Path(args.clips), timer)
    results = [(*item, checker(item[3], item[4])) for item in items]
    print(summarise(results, notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
