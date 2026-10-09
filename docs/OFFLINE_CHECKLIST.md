# Offline start: manual checklist

The tests for `scripts/` and the engine command line need no internet, Ollama, `torch` or weights, so they use stubs and fakes. They cannot prove the items below. Run this on a laptop that has everything installed, and tick it for P3-BE1-1 and P3-BE1-2.

## P3-BE1-1: one-command start (with internet once)
- [ ] `pip install -r engine/requirements.txt -r ai/requirements.txt` finishes (torch 2.8 is pinned; it was verified on Python 3.13 / Windows 11, not 3.14).
- [ ] `cd desktop && npm install` finishes.
- [ ] Ollama is installed and running.
- [ ] `python scripts/download_models.py` downloads the aligner (about 1.2 GB into `models/torch/`) and pulls `qwen2.5:7b`. Running it again says "already downloaded" for both.
- [ ] `scripts/start.sh --check` shows no `[MISSING]` item.
- [ ] `scripts/start.sh` opens the desktop app, the status pill shows the aligner as loaded, and a first reading is scored (the first start takes longer while the aligner loads).
- [ ] Closing the app leaves no `python -m app` and no `ollama serve` that `start.sh` started (check the process list).
- [ ] A fresh clone gets a database with the synthetic learners and passages on its first start.

## P3-BE1-2: airplane-mode run (Wi-Fi off)
- [ ] Turn Wi-Fi off, then `scripts/start.sh` starts with no network error.
- [ ] Sulat: make a book from a story and a model reading; playback highlights each word.
- [ ] Basa: record a reading, review it, override a word, confirm. The child's audio file under `engine/storage/audio/` is gone after confirm.
- [ ] Sanay: "Hear it" plays the word's clip; "Say it" works if P2-AI-2 is merged.
- [ ] The class view shows groups, with a draft plan (a template if Ollama is off).
- [ ] No request leaves the laptop (the pill never shows an error for being offline).
- [ ] Repeat on a clean laptop.
