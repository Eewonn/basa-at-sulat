# data/demo_checks/

Saved `ai.score()` results for the demo seed data (level, class view and progress screens). **Owner of the seed:** Backend 2 · **Produced by:** the AI engineer with `eval/run_eval.py --export-dir`.

One JSON per recording: `recording_id`, `passage_id`, `duration_sec`, and `score()`'s `words` (`i`, `text`, `label`, `score`, `start`, `end`) and `pauses`. No audio and no reader initials.

- **Source:** 23 Filipino test readings by one adult teammate with planted mistakes: 15 of `fil_g2_01` (the tuning set, `eval/ground_truth.csv`) and 8 of `fil_g2_02` / `fil_g2_03` (the confirmation set, `eval/confirm_ground_truth.csv`). Scored with the weakest-letter scoring from #13.
- **Not accuracy evidence.** These are the recordings the scoring was tuned and checked on. Quote `eval/REPORT.md` and `eval/CONFIRM_REPORT.md` for accuracy, never these.
- **Adult reading speed** (about 80–155 WCPM) puts every check at the top level. To show a range of levels, set `duration_sec` synthetically and scale `start`/`end` by the same factor.
- **No `heard` field:** `score()` aligns audio to the known passage and never transcribes what was said.
- `fil_g2_02` and `fil_g2_03` must be in the database before their checks load (they're added in `data/passages/passages.json`).

To regenerate after a scoring change: re-run `eval/run_eval.py` on each ground-truth file with `--export-dir data/demo_checks` (see `eval/README.md`).
