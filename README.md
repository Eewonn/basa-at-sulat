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

> ⚠️ Still unproven: whether "lines up badly" reliably means "misread". Task **P0-AI-1** tests this first, and it gates the rest of the build. See [docs/PLAN.md](docs/PLAN.md).

## Why it runs locally
1. **Children's voices** are minors' personal data and shouldn't leave the classroom.
2. **Many IP schools are offline**, in isolated areas with weak or no signal.
3. **The cloud has nothing better.** No cloud reading tool we found supports these languages.
4. **Instant and free.** Words light up seconds after reading, with no cost per child.

## Architecture (planned)

```
web/  (Next.js)  ──HTTP──►  engine/  (FastAPI, Python)
 recorder, review,            ├─ ai/      MMS aligner + word scoring (PyTorch, CPU)
 Sanay, Sulat, class view     ├─ SQLite   learners, passages, results, books
                              └─ Ollama   qwen2.5:3b for group plans
Everything runs on one laptop. No internet after setup.
```

## Repo layout

| Path | What | Owner |
|---|---|---|
| `ai/` | Alignment + word scoring module, Whisper fallback | AI engineer |
| `eval/` | Test recordings (adults, planted mistakes), ground truth, accuracy report | AI engineer |
| `engine/` | FastAPI service: audio pipeline, `/assess`, Sulat timings, word clips (Backend 1); database, levels, practice sets, plans, reports (Backend 2) | Backend 1 + 2 |
| `data/passages/` | Sample passages and seed data | Backend 2 |
| `web/` | Next.js 16 + TypeScript + Tailwind v4 app | Frontend |
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
Planning is done and Phase 0 (the aligner test) is next. No app code exists yet.

## Disclosures (to complete before submission)
Models and tools: Meta MMS forced aligner (**CC-BY-NC-4.0, non-commercial**), Qwen 2.5 3B via Ollama, Whisper (fallback only, if used), PyTorch, FastAPI, Next.js, SQLite. Internet is needed only to download models once. Test audio is recorded by adult team members with planted mistakes. No children's recordings are used.
