# Plan

## Goal
A top-10 finish among about 400 teams at the AppBuildersPH 2026 Local AI hackathon.

**Judging rubric (from the organizer's slides):** Problem & Usefulness 25 · Local AI Implementation 25 · Technical Execution 20 · Innovation 15 · Demo Quality 15.
The theme is AI running **on the user's device**, explicitly *not* "AI for a local audience". The IP-school angle earns points only through the local-AI reasons.

**Submission requires:** a working product built mostly during the hackathon, AI inference that runs locally in a meaningful way, a core feature that works without any cloud AI API, a public GitHub repo, a demo video plus an X/LinkedIn video URL, a statement of what runs locally versus what needs internet, disclosure of all models and tools, and an answer to "Why does this product benefit from running AI locally?"

## Phases
| Phase | Outcome | Gate |
|---|---|---|
| **0: aligner test** | We know whether MMS alignment can catch misread words | **Go if mistake-detection F1 is 0.6 or better** on our test set. Otherwise switch to the fallback |
| **1: core Basa** | Record → score → review → confirm, end to end | Works on 3 passages in 2 languages |
| **2: full loop** | Sulat books, Sanay practice, class view | A learner goes check → practice → re-check |
| **3: numbers and polish** | Accuracy report, offline one-command start, README, rehearsed demo | Airplane-mode run passes 3 times |

Tasks, owners and dependencies: [TASKS.md](TASKS.md).

### Fallback if Phase 0 fails
- **Filipino and English:** Whisper (faster-whisper small) prompted with the passage text, behind the same `score()` interface.
- **IP languages:** timing-only checks (speed, pauses, skips), and the teacher marks misreadings by hand.
- **Sanay:** "Hear it" and reread still work, because they only need the speaker's correct reading. "Say it" is dropped.
- **If even that fails:** fall back to our earlier idea, Room-as-Cloud (local AI file search across a team's devices).

## Top risks
| Risk | Mitigation |
|---|---|
| Mistake detection doesn't work | The Phase 0 gate and the fallback above |
| Test voices are adults, not children | Say so openly. Never record real children |
| "In seconds" overstates the time saving (the child still reads aloud) | P3-ALL-1: measure hand scoring versus Basa and quote the real number |
| No teacher on record (caps the Problem score) | P3-ALL-2: keep reaching out, and cite studies and public teacher posts |
| The live demo misfires | Scripted reading plus a backup video. "A judge reads" is a bonus only |
| MMS license is non-commercial | Disclose it. Fine for a hackathon |

## Scope rules
- **Basa is the hero.** Sanay closes the loop. Sulat stays small, because SIL's Bloom already makes talking books.
- No feature that needs speech recognition in IP languages, such as spoken comprehension questions.
- No AI-generated passages in IP languages: a small local model can't write them well.
- Anything not in TASKS.md is out of scope until the team agrees.
