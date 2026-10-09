"""The recording helper's planning and logging logic (no microphone needed)."""

import struct
import wave

import pytest

import metrics
import record
from record import Mistake

WORDS = "Nagtanim si Lina ng palay sa bukid. Masaya siya. Tinulungan siya ng kanyang lolo.".split()
HEADER = "recording_id,language,passage_id,word_index,expected,actual,error_type,reader,notes\n"


# --- parsing the plan -------------------------------------------------------

@pytest.mark.parametrize(
    "line, expected",
    [
        ("swap 4 pala", Mistake("swap", 4, "pala")),
        ("SWAP 4 pala", Mistake("swap", 4, "pala")),
        ("skip 12", Mistake("skip", 12)),
        ("insert 13 mabait", Mistake("insert", 13, "mabait")),
        ("insert 14 talaga", Mistake("insert", 14, "talaga")),  # after the last word
    ],
)
def test_parse_mistake(line, expected):
    assert record.parse_mistake(line, len(WORDS)) == expected


@pytest.mark.parametrize(
    "line, message",
    [
        ("swop 4 pala", "start with swap"),
        ("swap pala", "needs a word number"),
        ("swap 4", "needs the word you'll say"),
        ("skip 12 kanya", "only a word number"),
        ("skip 14", "0 to 13"),  # skip/swap must be a real passage word
        ("insert 15 x", "0 to 14"),
        ("insert 13 mabait na", "one word per line"),
        ("", "start with swap"),
    ],
)
def test_parse_mistake_rejects_with_a_helpful_message(line, message):
    with pytest.raises(ValueError, match=message):
        record.parse_mistake(line, len(WORDS))


def test_plan_warnings():
    assert record.plan_warnings([Mistake("swap", 4, "pala"), Mistake("skip", 12)]) == []
    assert any("next to each other" in w for w in record.plan_warnings([Mistake("skip", 4), Mistake("skip", 5)]))
    assert any("two mistakes" in w for w in record.plan_warnings([Mistake("skip", 4), Mistake("swap", 4, "x")]))
    assert any("2-3 is the target" in w for w in record.plan_warnings(
        [Mistake("skip", 0), Mistake("skip", 3), Mistake("skip", 6), Mistake("skip", 9)]))


# --- the script the reader sees ---------------------------------------------

def test_reading_script_applies_every_kind_of_mistake():
    plan = [Mistake("swap", 4, "pala"), Mistake("skip", 5), Mistake("insert", 13, "mabait"), Mistake("swap", 13, "lola")]
    script = record.reading_script(WORDS, plan)
    assert "ng [pala] bukid." in script  # swap shown, "sa" skipped
    assert "kanyang [mabait] [lola]." in script  # insert before word 13, swap keeps its full stop


def test_reading_script_clean_and_insert_at_the_end():
    assert record.reading_script(WORDS, []) == " ".join(WORDS)
    assert record.reading_script(WORDS, [Mistake("insert", len(WORDS), "talaga")]).endswith("lolo. [talaga]")


# --- ground-truth rows -------------------------------------------------------

def test_csv_rows_for_a_clean_reading():
    assert record.csv_rows("fil_001", "fil", "fil_g2_01", WORDS, [], "KM") == [
        ["fil_001", "fil", "fil_g2_01", "", "", "", "none", "KM", ""]
    ]


def test_csv_rows_strip_punctuation_from_expected_and_sort_by_word():
    plan = [Mistake("swap", 13, "lola"), Mistake("skip", 5), Mistake("insert", 9, "ang")]
    rows = record.csv_rows("fil_002", "fil", "fil_g2_01", WORDS, plan, "KM", "fan noise")
    assert rows == [
        ["fil_002", "fil", "fil_g2_01", "5", "sa", "", "skip", "KM", "fan noise"],
        ["fil_002", "fil", "fil_g2_01", "9", "", "ang", "insert", "KM", "fan noise"],
        ["fil_002", "fil", "fil_g2_01", "13", "lolo", "lola", "swap", "KM", "fan noise"],
    ]


def test_rows_round_trip_through_the_harness_parser(tmp_path):
    gt = tmp_path / "ground_truth.csv"
    gt.write_text(HEADER, encoding="utf-8")
    plan = [Mistake("swap", 4, "pala"), Mistake("skip", 12), Mistake("insert", 13, "mabait")]
    record.append_rows(gt, record.csv_rows("fil_002", "fil", "fil_g2_01", WORDS, plan, "KM", "fan, then chatter"))
    record.append_rows(gt, record.csv_rows("fil_003", "fil", "fil_g2_01", WORDS, [], "AB"))
    recs = metrics.load_ground_truth(gt)
    assert recs["fil_002"].errors == {4: "swap", 12: "skip"}
    assert recs["fil_002"].inserts == [13]
    assert recs["fil_003"].clean


# --- appending safely ---------------------------------------------------------

@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_append_keeps_the_files_line_endings(tmp_path, newline):
    gt = tmp_path / "ground_truth.csv"
    gt.write_bytes(HEADER.replace("\n", newline).encode())
    record.append_rows(gt, record.csv_rows("fil_001", "fil", "p", WORDS, [], "KM"))
    data = gt.read_bytes()
    assert data.count(newline.encode()) == 2
    if newline == "\n":
        assert b"\r" not in data


def test_append_adds_a_missing_final_newline(tmp_path):
    gt = tmp_path / "ground_truth.csv"
    gt.write_text(HEADER.rstrip("\n"), encoding="utf-8")
    record.append_rows(gt, record.csv_rows("fil_001", "fil", "p", WORDS, [], "KM"))
    assert "fil_001" in metrics.load_ground_truth(gt)


def test_append_rolls_back_if_the_result_wouldnt_parse(tmp_path):
    gt = tmp_path / "ground_truth.csv"
    gt.write_text(HEADER + "fil_001,fil,p,,,,none,KM,\n", encoding="utf-8")
    before = gt.read_bytes()
    bad = [["fil_001", "fil", "p", "3", "x", "y", "swap", "KM", ""]]  # clean recording can't also have a mistake
    with pytest.raises(metrics.GroundTruthError):
        record.append_rows(gt, bad)
    assert gt.read_bytes() == before


# --- recording ids -------------------------------------------------------------

def make_wav(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack("<h", 0) * 16)


def test_next_recording_id_starts_at_001(tmp_path):
    gt = tmp_path / "gt.csv"
    gt.write_text(HEADER, encoding="utf-8")
    assert record.next_recording_id("fil", tmp_path / "recordings", gt) == "fil_001"


def test_next_recording_id_looks_at_audio_and_ground_truth(tmp_path):
    gt = tmp_path / "gt.csv"
    gt.write_text(HEADER + "fil_004,fil,p,,,,none,KM,\neng_009,eng,p,,,,none,KM,\n", encoding="utf-8")
    make_wav(tmp_path / "recordings" / "fil" / "fil_002.wav")
    make_wav(tmp_path / "recordings" / "fil" / "fil_007.wav")  # audio someone else recorded, not logged yet
    make_wav(tmp_path / "recordings" / "fil" / "notes.wav")  # ignored: not an id
    assert record.next_recording_id("fil", tmp_path / "recordings", gt) == "fil_008"
    assert record.next_recording_id("eng", tmp_path / "recordings", gt) == "eng_010"


# --- level check --------------------------------------------------------------

def test_level_report_flags_quiet_short_and_clipping():
    import numpy as np

    quiet = np.full(16000 * 5, 100, dtype=np.int16)
    _, _, warnings = record.level_report(quiet, 16000)
    assert any("quiet" in w for w in warnings)
    short_loud = np.full(16000, 32767, dtype=np.int16)
    _, peak, warnings = record.level_report(short_loud, 16000)
    assert peak == 1.0
    assert any("clipping" in w for w in warnings) and any("too early" in w for w in warnings)
    good = (np.sin(np.linspace(0, 2000, 16000 * 5)) * 16000).astype(np.int16)
    assert record.level_report(good, 16000)[2] == []


# --- a whole session, with scripted keys and a fake microphone --------------------

def test_session_end_to_end(tmp_path, monkeypatch, capsys):
    import json

    import numpy as np
    import soundfile as sf

    passages = tmp_path / "passages.json"
    passages.write_text(json.dumps([{"id": "fil_g2_01", "title": "Ang Palay ni Lina", "language": "fil",
                                     "grade": 2, "text": " ".join(WORDS)}]), encoding="utf-8")
    gt = tmp_path / "ground_truth.csv"
    gt.write_text(HEADER, encoding="utf-8")
    recordings = tmp_path / "recordings"

    tone = (np.sin(np.linspace(0, 3000, 16000 * 6)) * 12000).astype(np.int16)
    monkeypatch.setattr(record, "record_until_enter", lambda device=None: (tone, 16000))
    keys = iter([
        # reading 1: clean, keep
        "", "", "k", "", "y",
        # reading 2: a typo, then two mistakes; redo once, then keep with a note
        "swop 4 pala", "swap 4 pala", "skip 12", "", "", "r", "", "k", "fan noise", "y",
        # reading 3: discard, then stop
        "skip 2", "", "", "d", "n",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(keys))

    code = record.main(["--reader", "KM", "--passages", str(passages), "--recordings", str(recordings),
                        "--ground-truth", str(gt)])
    out = capsys.readouterr().out
    assert code == 0
    assert "start with swap" in out  # the typo was explained, not crashed on
    assert "ng [pala] sa bukid." in out  # the script was shown

    recs = metrics.load_ground_truth(gt)
    assert sorted(recs) == ["fil_001", "fil_002"]  # the discarded reading wasn't logged
    assert recs["fil_001"].clean
    assert recs["fil_002"].errors == {4: "swap", 12: "skip"}
    assert sorted(p.name for p in (recordings / "fil").iterdir()) == ["fil_001.wav", "fil_002.wav"]
    info = sf.info(str(recordings / "fil" / "fil_002.wav"))
    assert (info.samplerate, info.channels, info.subtype) == (16000, 1, "PCM_16")
    assert "fan noise" in gt.read_text(encoding="utf-8")
