# eval/: test set and accuracy report

**Owner:** AI engineer (everyone records) · **Tasks:** P0-ALL-1, P0-AI-1, P3-AI-1

## Recording the test set (P0-ALL-1)
- **Adults only.** Never record children.
- About 10 readings per language: Filipino, English, and one regional language a teammate actually speaks.
- Use passages from `data/passages/`. In each reading, plant 2–3 mistakes and vary the type:
  - **swap:** say a different or similar word ("pala" for "palay")
  - **skip:** leave a word out
  - **insert:** add a word that isn't there
- Record a few clean readings too (no mistakes), so we can count false alarms.
- Add a little realism: some with a fan or background chatter on.
- Save files to `eval/recordings/<language>/<recording_id>.wav` (git-ignored). Share them through the team drive, not git.
- Log **every planted mistake** in `ground_truth.csv`, one row per mistake:

| column | example |
|---|---|
| recording_id | fil_007 |
| language | fil |
| passage_id | fil_g2_01 |
| word_index | 4 |
| expected | palay |
| actual | pala |
| error_type | swap / skip / insert |
| reader | initials |
| notes | fan noise |

Clean readings get one row with `error_type` = `none`.

**How to fill `word_index`:** split the passage text in `data/passages/passages.json` on spaces and count from 0, so in "Nagtanim si Lina ng palay sa bukid." the word `palay` is 4. Punctuation stays attached to its word (`bukid.`). For `swap` and `skip`, it's the passage word that was misread or left out.
For `insert` (an extra word the reader added), use the index of the passage word the extra word was said *before*.
`recording_id` must equal the file name (`fil_007` → `fil/fil_007.wav`), and `language` must match the folder. The test rejects a row that breaks these rules and names the row number.

## Running the test (P0-AI-1)
From the repo root, in the AI environment (`pip install -r ai/requirements-dev.txt`, see `ai/README.md`). The engine's environment alone is missing `soundfile` and torch:

```bash
python eval/run_eval.py            # scores every recording and writes eval/REPORT.md
python eval/run_eval.py --reuse    # rebuilds the report from the last run without re-running the model
python -m pytest eval              # checks the metric code itself
```

It reports precision, recall and F1 per language three ways: with the labels `score()` gives, with the best score cutoff, and with a cutoff chosen on half the recordings and tested on the other half. The go/no-go call uses the last one, because the best cutoff is tuned on the data it's measured on.
Inserted words are counted but kept out of F1, since they have no passage word to flag. Recordings listed in the ground truth but missing a `.wav` are skipped and named in the report.

## The report (P0-AI-1, then P3-AI-1)
`eval/REPORT.md` must show, per language: precision, recall and F1 for mistake detection, the reading-speed error versus a human scorer, and processing time per minute of audio on our CPU laptops. **Gate: F1 of 0.6 or better = go.**
