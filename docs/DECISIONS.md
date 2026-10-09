# Decision log

Newest first. Each entry: what we decided, and why.

## 2026-10-10: "Silid-aralan craft": make it look made for Filipino classrooms, not AI-made
Stock emoji, a sparkles icon and dashboard stat cards made the app look generated. We replaced them with our own illustrations in Taw's style and borrowed real classroom objects: the teacher's violet "VG / Very Good!" stamp, manila-paper flashcards with ruled lines, a reading card with a stamp per day, marker lettering for kid headings, a faint paper grain, the teacher's name and section in the greeting, and natural dates. Each signature element appears in one or two places so screens stay calm.

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
