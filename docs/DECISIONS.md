# Decision log

Newest first. Each entry: what we decided, and why.

## 2026-10-10: Reading level is a fluency-based estimate that uses CRLA's names
Every saved check gets a `level` (P1-BE2-2), computed in `engine/app/levels.py` from the final (overridden) labels. It uses the five reading levels on DepEd's CRLA submission form for SY 2026-27, lowest first: **Low Emerging, High Emerging, Developing, Transitioning, At Grade Level**. The same form has a second scale (Full / Moderate / Light Refresher, Grade Ready). That one is for the beginning-of-year letter and sound tasks, so we don't use it, and "At Grade Level" is not "Grade Ready".

**It is an estimate, not a CRLA result.** As far as we could find, CRLA places a child using two things: how much of the passage they read accurately within a time limit, and how many comprehension questions they answer correctly. This app asks no comprehension questions, and comprehension is what separates the upper levels in CRLA. So our level only estimates where a child's *fluency* sits on CRLA's scale. The app, the README and the demo must not present it as an official CRLA profile. A teacher-facing label such as "Estimated level (reading fluency)" is the honest wording.

**The rules.** Accuracy is `matched` words ÷ **the passage's word count**. We don't divide by the words the scorer returned, because the scorer may return a partial list and that would inflate accuracy.

| Level | Rule | Source |
|---|---|---|
| Low Emerging | 0 words correct | CRLA: "cannot read a single word accurately" |
| High Emerging | accuracy under 50% | CRLA: "less than 50% of the passage" |
| Developing | 50% to under 80% | **ours, pending teacher review** |
| Transitioning | at least 80%, but under 95% or under 40 WCPM | **ours, pending teacher review** |
| At Grade Level | at least 95% and at least 40 WCPM | 95%: **ours, pending teacher review**. 40 WCPM: see below |

40 WCPM comes from CRLA's own passages and time limits: 50 words in 1 minute (Grade 1), 95 in 2 (Grade 2), 120 in 3 (Grade 3), which works out to 40 to 50 words per minute to finish in time. 40 is the slowest of those rates. One threshold covers every grade and language for now (option B). Per-grade and per-language thresholds (option C) would need numbers we don't have yet.

**Pending teacher review:** the 80% and 95% cutoffs are our own picks. A teacher on the team should check them against how they would place real Grade 1 to 3 readers. If they change, only the constants at the top of `levels.py` and its tests change.

**Why not WCPM alone (option A):** a fast reader who misreads half the passage would rank too high. In our rules, speed only decides between Transitioning and At Grade Level.

**Gaps.** We couldn't find official numeric cutoffs. They seem to live only in DepEd's CRLA teacher manuals and scoresheets. The scoring details come from unofficial copies of the end-of-year CRLA slides, so they should be checked against an official manual if one turns up. Our passages (25 to 40 words) are also shorter than CRLA's (50 to 120), so percentages move in bigger steps: on a 23-word passage, each word is about 4%. Past results are not recomputed if the thresholds change.

**No `CHECK` on `level` yet.** The five names are fixed, but `schema.sql` doesn't enforce them. There are no migrations, so adding a constraint would make every teammate run `python -m app.init_db --reset` and lose their local data. `levels.py` is the only code that writes `level`, so the risk is low. **To do (P3):** add `CHECK (level IN (...))` together with the next schema change that needs a reset anyway.

**Sources (checked 2026-10-10):** [DepEd BLD CRLA school submission form](https://bld.deped.gov.ph/crla) (level names, SY 2026-27); [CRLA EoSY slides](https://www.slideshare.net/slideshow/comprehensive-rapid-literacy-assessment-crla-eosy-final-1-pptx/276427333) (passage %, time limits, comprehension, passage lengths); [General overview of CRLA](https://www.slideshare.net/slideshow/general-overview-of-crlapptx/258713065) (the beginning-of-year Refresher scale).

## 2026-10-10: Group plans are templates plus one model sentence from Qwen 2.5 7B, in Filipino first
A draft group plan (P0-BE2-3, P2-BE2-3) is a **teacher-style activity template** (`engine/prompts/activities-fil.json`) filled with the group's missed words, plus **one example sentence** written by **qwen2.5:7b** running locally in Ollama (offline, laptop CPU). The sentence is kept only if it passes checks (one line, 3 to 20 words, not repetitive, Latin letters only, no English or Spanish words from a short blocklist, uses a missed word). A rejected sentence is retried with up to 3 fixed seeds. If Ollama is down or every try is rejected, the plan is the template alone, and the reason is logged. Plans are **Filipino only for now**; English and regional languages come later. Prompt instructions are in English, with a firm rule to reply in Filipino. A native speaker reviews the templates and saved examples before the task is ticked.

**Why not let the model write the whole plan:** tested on 2026-10-09 and 10 with qwen2.5:3b, whole activities came out garbled and repetitive ("mga mga kahoy…", made-up words). Adding a Filipino example to the prompt made it readable, but the model just copied the example. Asked for only one sentence, 3B still wrote ungrammatical Filipino ("Ng mga tao sa salamin ng siya.") and, in 2 of 10 samples, words with Cyrillic letters.

**Why 7B:** across 10 samples (5 seeds × 2 word groups), 7B had no made-up words and no Cyrillic. It still slipped in English ("park", "toy") and broke down when told to use *all* the missed words. Three prompt fixes resolved most of this: use *at least one* of the words; varied examples (the model copies the first one); and, for groups that missed only function words (ng, sa, mga, siya), a separate prompt that limits the other words to a fixed list of simple ones (`sentence-small-words-fil.txt`). Without that list, those groups got nonsense such as "Siya ay may mga kapatid sa paglalaro sa hulugan." Final samples: "Kumain ng tinapay ang bata sa bakuran." and "Nagtanim ang ama, tinulungan ng ina." The checks can't tell whether a grammatical sentence makes sense, so native-speaker review still matters.

**Cost:** about 5 GB of RAM while loaded (2 GB for 3B), and 1.5 to 7 s per sentence on CPU once loaded, with about 9 s extra to load the model on first use. Runs on CPU aren't fully reproducible even with a fixed seed, so the same group can get a different sentence in another session.

**License:** Qwen2.5-7B-Instruct is **Apache 2.0** (checked on the Hugging Face model card and LICENSE file, 2026-10-10), so the research-only limits of Qwen2.5-3B's **Qwen RESEARCH LICENSE AGREEMENT** no longer apply. Distribution still needs the Apache 2.0 license copy and notices. This goes in the model disclosures (P3-AI-2) next to MMS's CC-BY-NC-4.0. The model is a setting (`OLLAMA_MODEL`); switching back to 3B would bring back the research-only license.

## 2026-10-10: Playful, BOOKR-inspired look with a tamaraw mascot
The whole app moved from the calm navy and cream look to bright color-block cards, rounded Nunito type and a BOOKR Class-style sidebar, because the app is used next to children and needs to feel friendly in the demo. Gamification is limited to stat cards (stars, days in a row, reading time) and story categories; badges and levels were left out to keep scope small. The mascot is an original tamaraw (a Philippine endemic animal) drawn as SVG; illustrations are Microsoft Fluent Emoji (MIT). The team deck still uses the old palette.

## 2026-10-09: Electron desktop app instead of a localhost web app
It has to run on Windows and Linux as a local-AI desktop app. Electron ships the same Chromium on both, so microphone recording behaves identically. Tauri's Linux webview (WebKitGTK) silently denies microphone access unless the app adds a custom permission handler. The interface uses Vite + React + TypeScript + Tailwind v4 (Next.js brings a server we don't need). The app starts the Python engine itself on a free local port. Full design: `docs/FRONTEND.md`.

## 2026-10-09: Product name is still open
"Basa at Sulat" is the working name. **Pakinig** ("listen") is the leading alternative because it describes what the app does. Other candidates: Sabay, Usbong, Pantig, Tanglaw. Avoid *Basa Pilipinas* (a USAID program), *BIGKAS* (an existing project) and *Tingog* (a party-list). **To do:** check the Play Store, GitHub and Google for conflicts, then decide.

## 2026-10-09: Add Sanay (practice) as the third mode
Basa only finds problems. Sanay turns each child's missed words into practice (hear it, say it, reread it), which closes the loop and shows growth at the next check. It reuses the same engine and the word clips from Sulat, so it needs no new model. It gets built after Basa works.

## 2026-10-09: Keep Sulat small
SIL's Bloom already makes free talking books with word highlighting in 1,000+ languages, and they play offline. Pitching Sulat as a big feature invites "that's Bloom." Sulat's job is to turn any story into a Basa passage with a model reading.

## 2026-10-09: Test the aligner before building
The core claim, that alignment confidence reveals misreadings, is unproven. Published child-speech work with Whisper only reached F1 of about 0.5 on Dutch children's reading mistakes. Phase 0 tests our approach on adult recordings with planted mistakes, and the Phase 0 gate in PLAN.md decides go or fallback.

## 2026-10-09: Use forced alignment, not speech recognition
In a reading check we already know the text. Meta's MMS aligner works letter by letter on any Latin-script text and can't "auto-correct" a misreading. Speech recognizers need per-language training, and research shows they tend to clean up children's errors.

## 2026-10-09: The teacher confirms every result
A 2022 DepEd and USAID/RTI computer-based reading pilot found AI scoring "not accurate or reliable enough" to stand alone, and cancelled its second phase. Our AI pre-scores and the teacher confirms or fixes each flagged word.

## 2026-10-09: Everything runs on one laptop, offline
The data is children's voices, many target schools are poorly connected, no cloud tool supports these languages, and scoring has to be instant. Internet is used only to download models once.

## 2026-10-09: No real children's recordings
All test and demo audio is recorded by adult teammates with planted mistakes. Accuracy on real children's speech is unknown, and we say so.
