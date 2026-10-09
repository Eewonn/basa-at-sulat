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

## The report (P0-AI-1, then P3-AI-1)
`eval/REPORT.md` must show, per language: precision, recall and F1 for mistake detection, the reading-speed error versus a human scorer, and processing time per minute of audio on our CPU laptops. **Gate: F1 of 0.6 or better = go.**
