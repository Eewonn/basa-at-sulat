"""Check word timings by ear (P2-AI-1): one HTML page per recording.

    python eval/timing_check.py fil_001 fil_016 fil_020

Each page plays the reading with every word highlighted as it's spoken (what Sulat's player will do), and
clicking a word plays only that word's clip (what Sanay's "Hear it" will play). Listen for clips that cut
off the start or end of a word, or that catch a bit of the next one. Use clean readings: word_timings() is
for a fluent speaker's correct reading.

Pages go to eval/out/timing_check/ (git-ignored). The audio is embedded, so each page works on its own.
"""
import argparse
import base64
import csv
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GROUND_TRUTH_FILES = (HERE / "ground_truth.csv", HERE / "confirm_ground_truth.csv")

PAGE = """<!doctype html>
<html lang="fil"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Timing check {rid}</title>
<style>
  body {{ font: 22px/1.8 system-ui, sans-serif; max-width: 760px; margin: 24px auto; padding: 0 16px; background: #fff; color: #111; }}
  .w {{ cursor: pointer; padding: 2px 4px; border-radius: 6px; }}
  .w:hover {{ outline: 2px solid #90caf9; }}
  .on {{ background: #ffd54f; }}
  button {{ font: inherit; padding: 6px 16px; }}
  small, table {{ font-size: 14px; color: #555; }}
  td {{ padding: 0 10px; }}
</style></head><body>
<h1 style="font-size:20px">{rid} · {title}</h1>
<p><button id="play">▶ Play the reading</button> <small>Click any word to hear only its clip.</small></p>
<p id="text">{spans}</p>
<audio id="audio" src="data:audio/wav;base64,{audio}"></audio>
<details><summary><small>Timings</small></summary><table>{rows}</table></details>
<script>
const T = {timings};
const audio = document.getElementById("audio");
const words = [...document.querySelectorAll(".w")];
let stopAt = null;
function tick() {{
  const t = audio.currentTime;
  words.forEach((el, k) => el.classList.toggle("on", !audio.paused && t >= T[k].start && t < T[k].end));
  if (stopAt !== null && t >= stopAt) {{ audio.pause(); stopAt = null; }}
  if (!audio.paused) requestAnimationFrame(tick); else words.forEach(el => el.classList.remove("on"));
}}
audio.addEventListener("play", () => requestAnimationFrame(tick));
document.getElementById("play").onclick = () => {{ stopAt = null; audio.currentTime = 0; audio.play(); }};
words.forEach((el, k) => el.onclick = () => {{ stopAt = T[k].end; audio.currentTime = T[k].start; audio.play(); }});
</script>
</body></html>
"""


def find_recording(rec_id: str) -> tuple:
    """(language, passage_id) for a recording, from either ground-truth file."""
    for path in GROUND_TRUTH_FILES:
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["recording_id"] == rec_id:
                        return row["language"], row["passage_id"]
    raise SystemExit(f"{rec_id} isn't in {' or '.join(p.name for p in GROUND_TRUTH_FILES)}")


def build_page(rec_id: str, title: str, audio_bytes: bytes, timings: list) -> str:
    spans = " ".join(f'<span class="w">{html.escape(t["text"])}</span>' for t in timings)
    rows = "".join(
        f"<tr><td>{t['i']}</td><td>{html.escape(t['text'])}</td><td>{t['start']:.2f}</td><td>{t['end']:.2f}</td></tr>"
        for t in timings
    )
    return PAGE.format(rid=html.escape(rec_id), title=html.escape(title), spans=spans, rows=rows,
                       audio=base64.b64encode(audio_bytes).decode("ascii"),
                       timings=json.dumps([{"start": t["start"], "end": t["end"]} for t in timings]))


def main(argv=None, timer=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording_ids", nargs="+", help="e.g. fil_001 fil_016 fil_020")
    ap.add_argument("--recordings", default=HERE / "recordings")
    ap.add_argument("--passages", default=ROOT / "data" / "passages" / "passages.json")
    ap.add_argument("--out", default=HERE / "out" / "timing_check")
    args = ap.parse_args(argv)

    if timer is None:
        sys.path.insert(0, str(ROOT))
        import ai

        timer = ai.word_timings
    passages = {p["id"]: p for p in json.loads(Path(args.passages).read_text(encoding="utf-8"))}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for rec_id in args.recording_ids:
        language, passage_id = find_recording(rec_id)
        audio = Path(args.recordings) / language / f"{rec_id}.wav"
        passage = passages[passage_id]
        page = out / f"{rec_id}.html"
        page.write_text(build_page(rec_id, passage["title"], audio.read_bytes(), timer(str(audio), passage["text"])),
                        encoding="utf-8")
        print(f"wrote {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
