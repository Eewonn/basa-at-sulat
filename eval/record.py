"""Record a test reading and log its planted mistakes in one go (P0-ALL-1).

    pip install -r eval/requirements-record.txt      # once (small: no torch)
    python eval/record.py --reader KM                 # Filipino passage fil_g2_01 by default
    python eval/record.py --reader KM --passage eng_g2_01
    python eval/record.py --list-devices              # if the wrong microphone is picked

For each reading it:
  1. shows the passage with word numbers,
  2. asks which mistakes you'll plant (swap / skip / insert), or none for a clean reading,
  3. shows the exact script to read, with the mistakes in [brackets],
  4. records from the mic until you press Enter, and checks the level,
  5. on "keep": saves eval/recordings/<language>/<id>.wav and appends the matching rows to
     eval/ground_truth.csv, then re-reads the file to make sure it still parses.

Adults only. Never record children.
"""
import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import metrics  # noqa: E402

SAMPLE_RATE = 16000
KINDS = ("swap", "skip", "insert")
_EDGE_PUNCTUATION = ".,!?;:\"()[]“”‘’'"


@dataclass(frozen=True)
class Mistake:
    kind: str  # "swap" | "skip" | "insert"
    index: int  # passage word; for insert, the word the extra word is said before
    said: str = ""  # what the reader says instead (swap) or adds (insert)


def bare(word: str) -> str:
    """The word without surrounding punctuation, for the expected/actual columns ("lolo." -> "lolo")."""
    return word.strip(_EDGE_PUNCTUATION)


def parse_mistake(line: str, n_words: int) -> Mistake:
    """"swap 4 pala" | "skip 12" | "insert 13 mabait". Raises ValueError with a message for the reader."""
    parts = line.split()
    if not parts or parts[0].lower() not in KINDS:
        raise ValueError("start with swap, skip or insert, e.g. 'swap 4 pala', 'skip 12', 'insert 13 mabait'")
    kind = parts[0].lower()
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError(f"{kind} needs a word number, e.g. '{kind} 4'")
    index = int(parts[1])
    last = n_words if kind == "insert" else n_words - 1  # an insert can go after the last word
    if index > last:
        raise ValueError(f"word number must be 0 to {last}")
    said = " ".join(parts[2:])
    if kind in ("swap", "insert") and not said:
        raise ValueError(f"{kind} needs the word you'll say, e.g. '{kind} {index} pala'")
    if kind == "skip" and said:
        raise ValueError("skip takes only a word number, e.g. 'skip 12'")
    if kind == "insert" and len(said.split()) > 1:
        raise ValueError("insert one word per line, so each extra word gets its own row")
    return Mistake(kind, index, said)


def plan_warnings(plan: list) -> list:
    """Problems that won't break anything but make the test less clear."""
    warnings = []
    word_level = [m for m in plan if m.kind != "insert"]
    seen = {}
    for m in word_level:
        if m.index in seen:
            warnings.append(f"word {m.index} has two mistakes ({seen[m.index]} and {m.kind}); keep one")
        seen[m.index] = m.kind
    indices = sorted({m.index for m in plan})
    for a, b in zip(indices, indices[1:]):
        if b - a <= 1:
            warnings.append(f"mistakes at words {a} and {b} are next to each other; spread them out so we can tell which one was flagged")
    if len(plan) > 3:
        warnings.append(f"{len(plan)} mistakes in one reading; 2-3 is the target")
    return warnings


def reading_script(words: list, plan: list) -> str:
    """What to actually say: swaps and inserts in [brackets], skipped words left out."""
    swaps = {m.index: m.said for m in plan if m.kind == "swap"}
    skips = {m.index for m in plan if m.kind == "skip"}
    inserts = {}
    for m in plan:
        if m.kind == "insert":
            inserts.setdefault(m.index, []).append(m.said)
    out = []
    for i, word in enumerate(words + [""]):
        out += [f"[{w}]" for w in inserts.get(i, [])]
        if i == len(words) or i in skips:
            continue
        if i in swaps:
            core = bare(word)
            out.append(word.replace(core, f"[{swaps[i]}]", 1) if core else f"[{swaps[i]}]")
        else:
            out.append(word)
    return " ".join(out)


def csv_rows(rec_id: str, language: str, passage_id: str, words: list, plan: list, reader: str, notes: str = "") -> list:
    """ground_truth.csv rows for one reading (column order as in the file's header)."""
    if not plan:
        return [[rec_id, language, passage_id, "", "", "", "none", reader, notes]]
    rows = []
    for m in sorted(plan, key=lambda m: (m.index, m.kind)):
        expected = bare(words[m.index]) if m.kind != "insert" else ""
        rows.append([rec_id, language, passage_id, str(m.index), expected, m.said, m.kind, reader, notes])
    return rows


def next_recording_id(language: str, recordings_dir: Path, ground_truth: Path) -> str:
    """The next free <language>_NNN, looking at both the audio files and the ground truth."""
    pattern = re.compile(rf"^{re.escape(language)}_(\d+)$")
    used = [0]
    folder = Path(recordings_dir) / language
    if folder.is_dir():
        used += [int(m.group(1)) for f in folder.glob("*.wav") if (m := pattern.match(f.stem))]
    if Path(ground_truth).exists():
        with open(ground_truth, newline="", encoding="utf-8") as f:
            used += [int(m.group(1)) for row in csv.DictReader(f) if (m := pattern.match((row.get("recording_id") or "").strip()))]
    return f"{language}_{max(used) + 1:03d}"


def append_rows(ground_truth: Path, rows: list) -> None:
    """Append rows, then re-read the whole file with the harness's parser. On any error, put the file back."""
    path = Path(ground_truth)
    before = path.read_bytes()
    newline = "\r\n" if b"\r\n" in before else "\n"  # match the file (git may check it out with CRLF)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            if before and not before.endswith(b"\n"):
                f.write(newline)
            csv.writer(f, lineterminator=newline).writerows(rows)
        metrics.load_ground_truth(path)
    except Exception:
        path.write_bytes(before)
        raise


def level_report(samples, sample_rate: int) -> tuple:
    """(seconds, peak 0-1, warnings) for int16 samples."""
    import numpy as np

    seconds = len(samples) / sample_rate
    peak = float(np.abs(samples.astype(np.int32)).max()) / 32767 if len(samples) else 0.0
    warnings = []
    if seconds < 3:
        warnings.append(f"only {seconds:.1f} s long; did it stop too early?")
    if peak < 0.05:
        warnings.append("very quiet; move closer to the mic or check the input device")
    if peak >= 0.99:
        warnings.append("clipping (too loud); move back a little")
    return seconds, peak, warnings


# --- microphone (not unit-tested: needs a real device) ----------------------

def record_until_enter(device=None):
    """Record mono int16 until Enter. Returns (samples, sample_rate). Tries 16 kHz, else the device's own rate."""
    import queue

    import numpy as np
    import sounddevice as sd

    try:
        sd.check_input_settings(device=device, samplerate=SAMPLE_RATE, channels=1, dtype="int16")
        rate = SAMPLE_RATE
    except Exception:
        rate = int(sd.query_devices(device, kind="input")["default_samplerate"])  # the aligner resamples anyway
    chunks = queue.Queue()

    def callback(indata, frames, time_info, status):
        chunks.put(indata.copy())

    with sd.InputStream(samplerate=rate, channels=1, dtype="int16", device=device, callback=callback):
        input("  ● recording... press Enter to stop ")
    parts = []
    while not chunks.empty():
        parts.append(chunks.get())
    return (np.concatenate(parts)[:, 0] if parts else np.zeros(0, dtype="int16")), rate


# --- interactive session ----------------------------------------------------

def show_passage(words: list) -> None:
    per_line = 6
    for start in range(0, len(words), per_line):
        print("  " + "  ".join(f"{i:>2} {w}" for i, w in enumerate(words[start:start + per_line], start)))


def ask_plan(words: list) -> list:
    print("\nPlan the mistakes, one per line ('swap 4 pala', 'skip 12', 'insert 13 mabait').")
    print("Press Enter on an empty line when done. Enter right away = clean reading.")
    plan = []
    while True:
        line = input("  mistake> ").strip()
        if not line:
            return plan
        try:
            plan.append(parse_mistake(line, len(words)))
        except ValueError as err:
            print(f"  ✗ {err}")


def session(args) -> int:
    passages = {p["id"]: p for p in json.loads(Path(args.passages).read_text(encoding="utf-8"))}
    if args.passage not in passages:
        print(f"no passage {args.passage!r}; choose from: {', '.join(passages)}")
        return 1
    passage = passages[args.passage]
    words, language = passage["text"].split(), passage["language"]

    print(f"\nRecording {passage['title']} ({args.passage}, {language}) as reader {args.reader}. Adults only.")
    while True:
        rec_id = next_recording_id(language, args.recordings, args.ground_truth)
        print(f"\n=== {rec_id} ===")
        show_passage(words)
        plan = ask_plan(words)
        for w in plan_warnings(plan):
            print(f"  ! {w}")
        print("\nRead this, naturally (don't stress the [bracketed] words):\n")
        print("  " + reading_script(words, plan) + "\n")
        if input("Press Enter to start recording (q to quit) ").strip().lower() == "q":
            return 0
        while True:
            samples, rate = record_until_enter(args.device)
            seconds, peak, warnings = level_report(samples, rate)
            print(f"  {seconds:.1f} s, peak level {peak:.0%}")
            for w in warnings:
                print(f"  ! {w}")
            choice = input("  [k]eep, [r]edo, [d]iscard? ").strip().lower()
            if choice != "r":
                break
            input("Press Enter to start again ")
        if choice == "k":
            notes = input("  notes (e.g. 'fan noise', Enter for none): ").strip()
            out = Path(args.recordings) / language / f"{rec_id}.wav"
            out.parent.mkdir(parents=True, exist_ok=True)
            import soundfile as sf

            sf.write(str(out), samples, rate, subtype="PCM_16")
            rows = csv_rows(rec_id, language, args.passage, words, plan, args.reader, notes)
            try:
                append_rows(args.ground_truth, rows)
            except Exception as err:
                out.unlink(missing_ok=True)
                print(f"  ✗ couldn't log it, so the recording wasn't kept: {err}")
                continue
            print(f"  ✓ saved {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} and {len(rows)} row(s) in ground_truth.csv")
        else:
            print("  discarded")
        if input("\nAnother reading? [Y/n] ").strip().lower() == "n":
            return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reader", help="your initials, e.g. KM")
    ap.add_argument("--passage", default="fil_g2_01")
    ap.add_argument("--device", default=None, help="input device number or name (see --list-devices)")
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--passages", default=ROOT / "data" / "passages" / "passages.json")
    ap.add_argument("--recordings", default=HERE / "recordings")
    ap.add_argument("--ground-truth", default=HERE / "ground_truth.csv")
    args = ap.parse_args(argv)
    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return 0
    if not args.reader:
        ap.error("--reader is required (your initials)")
    if isinstance(args.device, str) and args.device.isdigit():
        args.device = int(args.device)
    try:
        return session(args)
    except (KeyboardInterrupt, EOFError):
        print("\nstopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
