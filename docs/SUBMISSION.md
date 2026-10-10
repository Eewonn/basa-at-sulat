# Hackathon submission (AppBuildersPH 2026 Local AI)

Answers for the submission form. Fill in the two video URLs before submitting.

## The Project

**Project Name:** Basa at Sulat

**Short Description:** Basa at Sulat is an offline literacy tool that helps teachers in Indigenous Peoples' schools assess reading skills and create culturally relevant learning materials in Philippine languages.

Basa assesses students as they read aloud, identifying misread, skipped, and hesitated words, measuring reading fluency, and generating personalized exercises based on their reading difficulties.

Sulat enables teachers to turn community stories into interactive read-along books narrated by fluent local speakers, supporting literacy while preserving Indigenous languages and cultural heritage.

**Team Members:**
- Diaz, Mark Eron
- Magugat, Zio Gregory
- Mejia, Klyde Hedrick
- Santos, Marianne Angelika

**Public Github Repository:** https://github.com/Eewonn/basa-at-sulat

## The Proof

**Demo Video:** _TODO_

**X / LinkedIn Video URL:** _TODO_

**What runs locally?** All components operate offline on a single Windows or Linux laptop:
- **Electron** — Desktop interface for recording, reading assessments, class monitoring, practice activities, and read-along books.
- **FastAPI** — Local backend that starts automatically with the application.
- **Meta MMS** — CPU-based forced alignment for word-level assessment, audio synchronization, and individual word checks.
- **Qwen 2.5 7B (Ollama)** — Local AI model for generating group learning activities.
- **SQLite** — Local database for learner profiles, reading materials, assessment results, and storybooks.
- **FFmpeg** — Audio processing and format conversion.

All processing and storage happen on-device. No learner data or audio recordings are sent to external servers.

**What requires internet?** Only the initial setup, which includes downloading the Meta MMS model (1.26 GB, automatically downloaded on first launch), installing Qwen 2.5 7B through Ollama (4.7 GB), and setting up the required Python and Node.js dependencies. Once installed, all features operate entirely offline, with no further internet connection required.

**Hardware tested on:** Windows and Linux laptops, running entirely on the CPU (no GPU required).

**Why does this product benefit from running AI locally?**
1. **Children's voices stay in the classroom.** Every reading check is a recording of a minor. On-device scoring means no child's voice is uploaded, stored by a third party or used to train someone else's model.
2. **IP schools are often offline.** Many are in isolated areas with weak or no signal. After setup, the whole product runs with no internet. A cloud tool would stop working in exactly the schools that need it most.
3. **The cloud has nothing better.** We found no cloud speech or reading-assessment service that supports these languages. Because the text being read is already known, we *align* the child's voice to it with Meta's MMS forced aligner, which works letter by letter on any Latin-script language and runs on a CPU.
4. **Instant and free per child.** Words get flagged seconds after the child finishes reading, with no per-request cost or API quota.

## The Disclosures

**Models used:**
- **Meta MMS forced aligner** (wav2vec 2.0, 315M parameters), loaded through `torchaudio.pipelines.MMS_FA` (torchaudio 2.8.0). It runs with int8 weights for scoring and timings and at full precision for single-word checks. It is not retrained. License: CC-BY-NC 4.0.
- **Qwen 2.5 7B Instruct**, Ollama `qwen2.5:7b` (Q4_K_M GGUF, 4.7 GB). License: Apache 2.0.
- We use no cloud AI models. Whisper and uroman were considered but not used.

**Technologies and frameworks:**
- Desktop: Electron, electron-vite, React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Router, Radix UI
- Engine: Python, FastAPI, Uvicorn, PyTorch 2.8.0, torchaudio 2.8.0, NumPy, soundfile, SQLite, ffmpeg, Ollama
- Testing: pytest

**APIs and cloud services:** None at runtime. The models are downloaded once, from Meta's `dl.fbaipublicfiles.com` (through torchaudio) and the Ollama library.

**Existing code and assets:**
- Pretrained MMS aligner weights (Meta AI) and Qwen 2.5 weights (Alibaba's Qwen team)
- Open-source libraries: lucide-react icons, Radix UI primitives, and the Nunito and Patrick Hand fonts (through Fontsource)
- Passages `fil_g2_01` and `eng_g2_01` were written by the team. `fil_g2_02` and `fil_g2_03` were drafted by Claude and checked by a native Filipino speaker on the team.
- Seed learners are synthetic (made-up first names). Demo checks start from real scores on adult test readings, and some were relabelled by hand to show lower reading levels. They are for display only, not evidence of accuracy.
- We used no children's recordings. The test audio is 23 Filipino readings by one adult team member with planted mistakes.

**AI development tools:** Claude Code (Anthropic) as a coding assistant. Claude also drafted two of the test passages, which a team member then reviewed.
