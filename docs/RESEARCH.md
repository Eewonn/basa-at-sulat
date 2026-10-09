# Research and evidence

Facts we use in the pitch, with sources. "Our arithmetic" marks numbers we calculated ourselves.

## The problem
- **About 91%** of Filipino 10-year-olds can't read and understand an age-appropriate text (World Bank learning poverty). [Inquirer](https://newsinfo.inquirer.net/1835164/ph-learning-poverty-still-among-regions-worst)
- National assessment (2023–2025): **30.5%** of Grade 3 learners are proficient at grade level, falling to 19.6% in Grade 6 (cited on the ADB country page).
- **CRLA**, DepEd's teacher-led reading screener, takes **5–8 minutes per child per language**, at the start, middle and end of the school year. [RTI](https://shared.rti.org/node/1124)
  - Our arithmetic: 35 learners × 5–8 min ≈ 3–5 hours per language, per round. That includes listening time, which Basa can't remove.
- **About 12,000** public schools lacked internet in 2025, mostly in geographically isolated and disadvantaged areas. Full connection was promised for end-2025, and we haven't confirmed whether it happened. [Inquirer](https://newsinfo.inquirer.net/2080790/deped-to-connect-all-public-schools-to-the-internet-within-2025)

## The IP-school gap
- RA 12027 and **DepEd Order 020 s.2025** make Filipino and English the main languages of instruction for K–3, but **schools in the IP education program are exempt** and may keep using the learner's language. [Philstar](https://philstarlife.com/news-and-views/198067-filipino-and-english-to-be-used-in-teaching-kinder-to-grade-3-students-deped)
- Studies of IP education report shortages of culturally adapted materials (Cordillera 2013, Davao 2024, Misamis Occidental 2025, Mamanwa learners in Southern Leyte). [UIC journal](https://ojs.uic.edu.ph/index.php/IJER/article/download/26/25/93)
- More than 160 languages across 500+ IP communities (SEAMEO, 2010). [SEAMEO](https://www.seameo.org/LanguageMDGConference2010/doc/track/Track1/Indigenous_Peoples_core_curriculum_in_the_philippines.pdf)

## Prior attempts and competitors
- **DepEd + USAID/RTI computer-based reading pilot (2022):** AI scoring was "not accurate or reliable enough" to stand alone, and the second pilot was cancelled. [Pilot report](https://ierc-publicfiles.s3.amazonaws.com/public/resources/CB%20Reading%20Assessment%20Pilot%20Report_Final.pdf)
- **Microsoft Reading Progress:** cloud-based (Teams), used in some Philippine schools. [Microsoft](https://news.microsoft.com/source/asia/2025/07/01/deped-and-microsoft-expand-ai-powered-literacy-initiatives-across-the-philippines/)
- **Google Read Along:** offline and on-device, but its nine languages don't include Filipino, and it's a practice app for kids, not an assessment tool. [Voice Summit](https://www.voicesummit.ai/blog/googles-new-reading-app-helps-kids-learn-through-voice)
- **BIGKAS:** an open-source project for Sagay City. It transcribes with Whisper and compares the transcript to the passage. [GitHub](https://github.com/clyd-dev/BIGKAS-AI)
- **Bloom (SIL):** talking books in 1,000+ languages with automatic audio splitting, offline playback in Bloom Reader. [Bloom docs](https://docs.bloomlibrary.org/Help/Reference/talking-book-tool-overview/)

## Technical basis
- **MMS forced aligner** (`torchaudio.pipelines.MMS_FA`): trained on 23,000 hours across 1,100+ languages, character-level, needs romanized text (uroman), has a `<star>` token for extra speech. License CC-BY-NC-4.0. [PyTorch tutorial](https://docs.pytorch.org/audio/2.8/tutorials/forced_alignment_for_multilingual_data_tutorial.html)
- **Comparing a transcript to the passage afterward** works poorly without a word-for-word transcript. Prompting Whisper with the passage helps. [Apple, Smith et al. 2025](https://arxiv.org/html/2505.23627v1)
- **Children's reading mistakes (Dutch):** the best mistake-detection F1 was about 0.52 (Whisper), and the best recall 0.83 (wav2vec2). [arXiv 2406.07060](https://arxiv.org/pdf/2406.07060)

## Not yet verified
- Which Philippine and IP languages MMS covers well.
- Whether torchaudio's current release still ships `forced_align`/`MMS_FA` (task P0-AI-2).
- DepEd's current CRLA reading-profile names.
- The 2026 school connectivity figure.
