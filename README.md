# Basa at Sulat

**Offline reading checks in any Philippine language, for teachers in IP schools.**
Working name. *Pakinig* ("listen") is the leading alternative, see [docs/DECISIONS.md](docs/DECISIONS.md).

Built for the **AppBuildersPH 2026 Local AI hackathon**: meaningful AI runs on the user's device, and the product stays useful when the cloud disappears.

## What it does

| Mode | What happens |
|---|---|
| **Sulat** (make) | A teacher types a story in the children's language. A fluent speaker (an elder, the teacher, a parent) reads it aloud, and it becomes a read-along book. |
| **Basa** (check) | A child reads the story aloud. The laptop flags misread, skipped and hesitated words. The teacher confirms with one tap and gets words correct per minute and a reading level. |
| **Sanay** (practice) | Each child practices the exact words they missed: hear it in the speaker's voice, say it, reread the sentence. The next Basa check shows the growth. |

## The core idea

Normal speech recognition has to guess *what* was said, which needs a model trained on that language. Most Philippine IP languages don't have one.

In a reading check **we already know the text**. So we only need to *line up* the child's voice with the known words, using Meta's MMS forced aligner. It works letter by letter on any Latin-script text, was trained on 1,100+ languages, and runs on a CPU. Words that line up badly are likely mistakes, and the aligner can't "auto-correct" a child the way Whisper-style recognizers tend to.

> ✅ Tested in Phase 0: on Filipino readings by an adult with planted mistakes, scoring each word by its weakest-fitting letter caught misread and skipped words with **F1 0.74** on fresh passages it was never tuned on (gate: 0.6). Not yet tested on English, regional languages, other voices or children. See [docs/DECISIONS.md](docs/DECISIONS.md) and [eval/CONFIRM_REPORT.md](eval/CONFIRM_REPORT.md).

## Why it runs locally
1. **Children's voices** are minors' personal data and shouldn't leave the classroom.
2. **Many IP schools are offline**, in isolated areas with weak or no signal.
3. **The cloud has nothing better.** No cloud reading tool we found supports these languages.
4. **Instant and free.** Words light up seconds after reading, with no cost per child.

## Architecture (planned)

```
desktop/ (Electron) ──HTTP──► engine/  (FastAPI, Python, started by the app)
 recorder, review,            ├─ ai/      MMS aligner + word scoring (PyTorch, CPU)
 Sanay, Sulat, class view     ├─ SQLite   learners, passages, results, books
                              └─ Ollama   qwen2.5:7b for group plans
Everything runs on one laptop. No internet after setup.
```

## Repo layout

| Path | What | Owner |
|---|---|---|
| `ai/` | Alignment + word scoring module, Whisper fallback | AI engineer |
| `eval/` | Test recordings (adults, planted mistakes), ground truth, accuracy report | AI engineer |
| `engine/` | FastAPI service: audio pipeline, `/assess`, Sulat timings, word clips (Backend 1); database, levels, practice sets, plans, reports (Backend 2) | Backend 1 + 2 |
| `data/passages/` | Sample passages and seed data | Backend 2 |
| `desktop/` | Electron + React + TypeScript + Tailwind v4 desktop app (Windows + Linux), see `docs/FRONTEND.md` | Frontend |
| `docs/` | Plan, tasks, API contract, decisions, research, demo script | Everyone |
| `scripts/` | Tooling (GitHub issue creation, later: one-command start) | Backend 1 |

## Team

| Role | Focus |
|---|---|
| **AI engineer** | Is the scoring right? Aligner test, scoring, fallback, accuracy and speed numbers |
| **Backend 1** | Engine service: audio in, word results out, Sulat timings, word clips, offline startup |
| **Backend 2** | Data and logic: database, levels, Sanay practice sets, group plans, reports, README |
| **Frontend** | Every screen: recorder, review, class view, Sanay, Sulat player, Filipino UI |

The full task board with owners, dependencies and "done when" criteria is in **[docs/TASKS.md](docs/TASKS.md)**.

## How we work
- **Pick a task** from [docs/TASKS.md](docs/TASKS.md) (or its GitHub issue) and put your name on it.
- **Branch per task:** `p1-fe-1-review-screen`. Use the task ID in the branch name and the PR title.
- **Small PRs**, one task each. Someone else reviews and merges.
- **Tick the box** in `docs/TASKS.md` in the same PR that finishes the task.
- **The API contract is law.** Change [docs/API.md](docs/API.md) first, tell the team, then change the code.
- **Never commit:** real children's recordings, model weights, `.env` files.

To turn the task board into GitHub issues after pushing:

```bash
python3 scripts/create_issues.py --dry-run   # preview
python3 scripts/create_issues.py             # creates labels + issues via gh
```

## Status
Phase 0 passed: the team chose **go** with the MMS aligner (see [docs/DECISIONS.md](docs/DECISIONS.md)). Phase 1 (record → score → review → confirm) is in progress; progress per task is in [docs/TASKS.md](docs/TASKS.md).

## Disclosures

### AI models (all run on the laptop)
| Model | What it does here | Exact version | License | Source |
|---|---|---|---|---|
| **Meta MMS forced aligner** (wav2vec 2.0, 315M parameters, trained on 31K hours in 1,130 languages) | Lines up a reading with the known text: word scores (Basa), word timings (Sulat), single-word checks (Sanay) | `torchaudio.pipelines.MMS_FA` in torchaudio 2.8.0; weights `ctc_alignment_mling_uroman/model.pt` (1.26 GB). We run it with int8 weights for scoring and timings, full precision for single-word checks; nothing is retrained | **CC-BY-NC 4.0 (non-commercial)** | Pratap et al., 2023, *Scaling Speech Technology to 1,000+ Languages* (Meta AI); weights from `dl.fbaipublicfiles.com` via torchaudio |
| **Qwen 2.5 7B Instruct** (7.6B parameters) | Writes one example sentence for each group's draft activity plan | Ollama `qwen2.5:7b` (= `7b-instruct-q4_K_M`), GGUF Q4_K_M, 4.7 GB, digest `sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` | **Apache 2.0** | Alibaba Cloud's Qwen team, via the Ollama library |

**Not used:** Whisper (the fallback wasn't needed once the aligner passed the Phase 0 test; see [docs/DECISIONS.md](docs/DECISIONS.md)), uroman (passages are normalised by our own code in `ai/text.py`), and any cloud AI API.

### Internet
Needed only once, to download the models: the MMS weights (1.26 GB, fetched on first start) and `qwen2.5:7b` (4.7 GB, `ollama pull qwen2.5:7b`), plus the Python and Node packages. After that, scoring, timings, word checks, group plans and storage all work offline.

### Tools
PyTorch 2.8.0 and torchaudio 2.8.0, FastAPI, SQLite, ffmpeg, Ollama, Electron, React, Vite, TypeScript, Tailwind CSS. Development used Claude Code (Anthropic) as a coding assistant.

### Data
- **No children's recordings are used.** The test recordings are 23 Filipino readings by one adult team member with planted mistakes (`eval/ground_truth.csv`, `eval/confirm_ground_truth.csv`); the audio stays off GitHub.
- Passages `fil_g2_01` and `eng_g2_01` were written by the team. `fil_g2_02` and `fil_g2_03` were drafted by Claude (AI) and checked by a native Filipino-speaking team member, for the confirmation test.
- Learners in the seed data are synthetic (made-up first names). The demo's saved checks start from real `score()` results on those adult test readings, slowed to a child's pace; some have words relabelled **by hand** to show lower levels and are synthetic, not model output (`data/demo_seed.json`). They're for display, never accuracy evidence.
