"""The timing-check page builder (no model, no real recordings)."""

import json
import struct
import wave

import timing_check


def test_page_embeds_audio_words_and_timings(tmp_path):
    rec = tmp_path / "recordings" / "fil"
    rec.mkdir(parents=True)
    with wave.open(str(rec / "fil_001.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack("<h", 0) * 1600)
    passages = tmp_path / "passages.json"
    passages.write_text(json.dumps([{"id": "p1", "title": "Ang <Palay>", "language": "fil", "grade": 2,
                                     "text": "Nagtanim si Lina."}]), encoding="utf-8")
    gt = tmp_path / "gt.csv"
    gt.write_text("recording_id,language,passage_id,word_index,expected,actual,error_type,reader,notes\n"
                  "fil_001,fil,p1,,,,none,KM,\n", encoding="utf-8")
    timing_check.GROUND_TRUTH_FILES = (gt,)

    def fake_timer(path, text):
        return [{"i": i, "text": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(text.split())]

    assert timing_check.main(["fil_001", "--recordings", str(tmp_path / "recordings"), "--passages", str(passages),
                              "--out", str(tmp_path / "out")], timer=fake_timer) == 0
    page = (tmp_path / "out" / "fil_001.html").read_text(encoding="utf-8")
    assert page.count('class="w"') == 3
    assert "data:audio/wav;base64,UklGR" in page  # a RIFF/WAV file is embedded
    assert '{"start": 1.0, "end": 1.4}' in page
    assert "Ang &lt;Palay&gt;" in page  # titles and words are escaped
    assert "KM" not in page
