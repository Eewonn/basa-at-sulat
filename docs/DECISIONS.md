# Decision log

Newest first. Each entry: what we decided, and why.

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
