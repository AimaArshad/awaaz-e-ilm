# Awaaz-e-Ilm: Architecture

> **Agent instructions:** Read this entire file before writing any code. It is the source of truth for scope, structure and conventions. If something here conflicts with a later prompt, ask before deviating. Build in small steps, run and test each step, and keep the README current.

---

## 1. Purpose

A voice-controlled web app for **visually impaired students** who currently depend on family members to record their study material. The user uploads a PDF, DOCX, image or scanned PDF. The system converts it into natural-sounding audio, split into chapters, in **English or Urdu**. The student controls everything by voice (and keyboard), with no need to see the screen.

### Must-have features
1. Upload: digital PDF, scanned PDF, DOCX, PNG/JPG images.
2. Text extraction with OCR for scanned files and images. Languages: **English and Urdu**.
3. Automatic **chapter detection**.
4. Neural **TTS** in English and Urdu.
5. **Translation** EN to UR and UR to EN, so the user can listen in either language.
6. **Voice commands** via STT (Whisper): chapter navigation, forward/back 30 seconds, pause/resume/stop, speed, language switch, and more.
7. Playback **starts with Chapter 1**; other chapters are processed in the background.
8. Resume where the user left off.
9. Accessible UI: keyboard-operable, screen-reader compatible, high contrast, spoken feedback for every action.
10. Describe figures and images inside documents (image recognition).

### Non-goals (for the demo)
Multi-tenant auth, payments, mobile native apps, cloud deployment.

### Hard constraints
- Use **free, open-source models** (Hugging Face or pip packages). No paid APIs required.
- Must run on a **laptop CPU**. GPU is optional and auto-detected.
- All processing is **local**. Do not send user documents to third-party services. (`edge-tts` is the only optional exception and must be off by default.)
- Document every model and its license in `docs/MODELS_AND_LICENSES.md`.

---

## 2. High-level pipeline

```
Upload (PDF / DOCX / image / scanned PDF)
        │
        ▼
Ingestion: detect file type, per-page "has text layer?" check
        │
        ├── text layer present ──► PyMuPDF text extraction
        └── no text layer / image ─► preprocessing (OpenCV) ► OCR (Tesseract eng+urd, EasyOCR fallback)
        │
        ▼
Figure/image handling: caption with Florence-2, insert "Figure: ..." text
        │
        ▼
Cleanup: remove headers/footers/page numbers, fix hyphenation, normalize Unicode
        │
        ▼
Language detection per paragraph (Arabic-script ratio + lingua)
        │
        ▼
Chapter detection (TOC → regex → font heuristics → page-chunk fallback)
        │
        ▼
For each chapter (Chapter 1 FIRST, rest in background):
   optional translation → sentence split → TTS per sentence
   → ffmpeg stitch into one MP3 per chapter + timing.json
        │
        ▼
Player + voice loop:
   push-to-talk → mic → VAD → faster-whisper → normalize → intent parser → action → spoken confirmation
```

**Latency goal:** Chapter 1 audio is playable within about 60 seconds of upload for a normal-sized book on CPU. Everything else streams in behind it.

---

## 3. Tech stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Queue | Celery + Redis (fallback: FastAPI BackgroundTasks behind a flag `USE_CELERY=false`) |
| Database | SQLite for the demo (SQLAlchemy + Alembic, Postgres-ready) |
| File storage | Local disk under `backend/storage/` (S3/MinIO-ready abstraction) |
| Audio | ffmpeg, pydub |
| Containers | Docker Compose (backend, worker, redis, frontend) |

### AI models

| Task | Primary | Fallback / notes |
|---|---|---|
| Digital PDF text | PyMuPDF | pdfplumber for tables |
| DOCX | python-docx | |
| OCR | Tesseract (`eng`, `urd`) via pytesseract / OCRmyPDF | EasyOCR (`en`, `ur`) |
| Image preprocessing | OpenCV (grayscale, deskew, denoise, threshold) | |
| Image captioning | `microsoft/Florence-2-base` | BLIP; optional Qwen2-VL-2B on GPU |
| Language detection | Unicode script ratio + `lingua-language-detector` | |
| Sentence splitting | `pysbd` (`en`, `ur`) | |
| Translation | `Helsinki-NLP/opus-mt-en-ur`, `Helsinki-NLP/opus-mt-ur-en` | `facebook/nllb-200-distilled-600M` (non-commercial license) |
| TTS English | Kokoro-82M | Piper |
| TTS Urdu | `facebook/mms-tts-urd-script_arabic` | `ai4bharat/indic-parler-tts` (verify Urdu support on the model card); optional `edge-tts` ur-PK voices, disabled by default |
| STT | `faster-whisper` (default model `small`, int8 on CPU; configurable) | Browser Web Speech API fallback on the frontend |
| VAD | Silero VAD | |
| Intent parsing | Rule-based patterns + `rapidfuzz` | Optional small LLM via Ollama, off by default |

All model names and sizes live in `backend/app/config.py` and `.env`, never hard-coded in services. Models load **lazily** and are cached in `backend/models_cache/`.

### Known limitations (state these in the README)
- Urdu OCR on Nastaliq-style or low-quality scans is error-prone.
- MMS Urdu TTS is intelligible but less natural than the English voices.
- Whisper Urdu accuracy is moderate, so voice commands use a constrained grammar.

---

## 4. Database schema

```
users(id, name, preferred_lang, speech_rate, created_at)

documents(id, user_id, title, filename, file_type, source_lang,
          status[uploaded|extracting|ready|failed], created_at)

chapters(id, document_id, index, title, text_path, lang,
         status[pending|processing|ready|failed])

audio_tracks(id, chapter_id, lang, voice, audio_path, duration_s, timing_path, created_at)

playback_state(user_id, document_id, chapter_index, position_s, speed, audio_lang, updated_at)

jobs(id, document_id, stage, progress, error, created_at, updated_at)

command_log(id, user_id, transcript, intent, params, success, created_at)
```

For the demo, a single default user is created automatically (no login).

---

## 5. API design

### REST
```
POST   /documents                      upload file (multipart), returns document + job id
GET    /documents                      list library
GET    /documents/{id}                 details + status
DELETE /documents/{id}
GET    /documents/{id}/chapters        chapter list with status
GET    /chapters/{id}/audio?lang=en|ur streams MP3 (generates translated track on demand)
GET    /chapters/{id}/timing?lang=     timing.json (sentence timestamps)
POST   /chapters/{id}/regenerate       rebuild a chapter's audio
GET    /playback/{document_id}         get saved state
PUT    /playback/{document_id}         save state
GET    /health
```

### WebSocket
```
/ws/progress/{document_id}   server pushes {stage, progress, chapter_ready: index}
/ws/voice                    client streams audio chunks;
                             server replies {transcript, intent, params, spoken_reply}
```

### timing.json format
```json
[
  {"idx": 0, "start_s": 0.0, "end_s": 3.42, "text": "Chapter One. Introduction."},
  {"idx": 1, "start_s": 3.42, "end_s": 8.1, "text": "..."}
]
```

---

## 6. Voice control design

Flow: `hold Space (or press-and-hold on touch) → record → VAD → Whisper → normalize text → intent parser → execute → spoken confirmation`

**Echo handling:** the mic must not hear the book. Default is push-to-talk. When push-to-talk begins, the frontend pauses or ducks audio. Enable `echoCancellation`, `noiseSuppression` and `autoGainControl` in `getUserMedia`. Wake word ("Hey Awaaz", openWakeWord) is an optional later feature.

### Intents

| Intent | English examples | Urdu / Roman Urdu examples | Params |
|---|---|---|---|
| `go_to_chapter` | "go to chapter 5", "chapter five", "move to chapter 5" | "باب پانچ پر جاؤ", "chapter paanch" | `n` |
| `next_chapter` / `prev_chapter` | "next chapter", "previous chapter" | "اگلا باب", "پچھلا باب" | |
| `forward_seconds` | "forward 30 seconds", "skip 30" | "30 سیکنڈ آگے" | `s` (default 30) |
| `back_seconds` | "back 30 seconds", "rewind 30" | "30 سیکنڈ پیچھے" | `s` (default 30) |
| `pause` | "pause", "stop" | "رکو", "روکو" | |
| `resume` | "play", "resume", "continue" | "چلاؤ", "جاری رکھو" | |
| `set_speed` | "faster", "slower", "speed 1.5" | "تیز", "آہستہ" | `rate` |
| `switch_language` | "read in Urdu", "read in English" | "اردو میں پڑھو", "انگریزی میں پڑھو" | `lang` |
| `where_am_i` | "what chapter is this" | "یہ کون سا باب ہے" | |
| `list_chapters` | "list chapters" | "ابواب بتاؤ" | |
| `repeat_sentence` | "repeat that" | "دوبارہ پڑھو" | |
| `open_book` | "open [title]" | "[title] کھولو" | `query` (fuzzy match) |
| `help` | "help" | "مدد" | |

Rules:
- Normalize number words in English, Urdu and Roman Urdu (`five`, `پانچ`, `paanch`, `5`) to integers before matching.
- Use fuzzy matching (rapidfuzz) to tolerate Whisper misrecognitions.
- Every command gets a **spoken confirmation** ("Going to chapter 5").
- Failure gets a spoken fallback ("Sorry, I didn't catch that. Say help for commands").
- If the target chapter is not ready: "Chapter 5 is still being prepared."
- Log every command to `command_log`.

### Seeking
Each chapter is one stitched MP3 plus `timing.json`. Forward and back are `currentTime ± 30`, and roll into the next or previous chapter at the boundaries.

---

## 7. Frontend requirements

- **Pages:** Library, Upload, Player (chapter list, transcript with sentence highlighting, controls), Settings (language, voice, speed, model size).
- **Voice-first:** a large push-to-talk control, with Space as the keyboard shortcut. Everything is also operable by keyboard.
- **Spoken feedback** for every state change (uploading, processing progress, chapter ready, errors), using short earcons plus TTS. Pre-generate common phrases in English and Urdu.
- **First launch:** the app speaks a short tutorial listing the main commands.
- **Audio player:** HTMLAudioElement, Media Session API (headset and lock-screen controls), speed control, resume from `playback_state` (save every 5 seconds and on pause).
- **Accessibility:** semantic HTML, ARIA live regions for announcements, skip links, visible focus, high-contrast theme, large text option, RTL support for Urdu text. Test with NVDA or VoiceOver.
- **Keyboard shortcuts:** Space (hold) talk, K play/pause, J/L back/forward 30s, N/P next/previous chapter, ? help.

---

## 8. Folder structure

```
awaaz-e-ilm/
├── README.md
├── docker-compose.yml
├── .env.example
├── Makefile
├── docs/
│   ├── ARCHITECTURE.md
│   ├── VOICE_COMMANDS.md
│   ├── MODELS_AND_LICENSES.md
│   └── DEMO_SCRIPT.md
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── documents.py
│   │   │   ├── chapters.py
│   │   │   ├── audio.py
│   │   │   ├── playback.py
│   │   │   └── voice_ws.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── ingestion.py
│   │   │   ├── text_extract.py
│   │   │   ├── ocr.py
│   │   │   ├── vision.py
│   │   │   ├── lang_detect.py
│   │   │   ├── cleanup.py
│   │   │   ├── chapters.py
│   │   │   ├── translate.py
│   │   │   ├── tts/
│   │   │   │   ├── base.py
│   │   │   │   ├── kokoro_en.py
│   │   │   │   ├── piper_en.py
│   │   │   │   └── mms_ur.py
│   │   │   ├── stt.py
│   │   │   ├── vad.py
│   │   │   ├── intent/
│   │   │   │   ├── parser.py
│   │   │   │   ├── numbers_en_ur.py
│   │   │   │   └── patterns.py
│   │   │   └── audio_stitch.py
│   │   ├── workers/
│   │   │   ├── celery_app.py
│   │   │   └── pipeline.py
│   │   └── utils/
│   ├── storage/              # gitignored: uploads, text, audio
│   ├── models_cache/         # gitignored: Hugging Face models
│   └── tests/
│       ├── test_intent.py
│       ├── test_chapters.py
│       ├── test_ocr.py
│       └── fixtures/         # sample EN/UR PDFs, scanned page, image
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/            # Library, Upload, Player, Settings
│   │   ├── components/       # VoiceButton, AudioPlayer, ChapterList, Transcript, ProgressBar
│   │   ├── hooks/            # useVoiceCommands, useAudioPlayer, useKeyboardShortcuts, useAnnouncer
│   │   ├── lib/              # api.ts, ws.ts, speak.ts, earcons.ts
│   │   └── styles/
│   └── public/earcons/
└── scripts/
    ├── download_models.py
    ├── seed_demo_data.py
    └── benchmark_ocr_tts.py
```

---

## 9. Engineering conventions

- Python: type hints, Pydantic schemas, `ruff` + `black`, `pytest`. Frontend: strict TypeScript, ESLint, Prettier.
- **TTS interface:** every engine implements `synthesize(text, lang, voice) -> AudioSegment` in `services/tts/base.py`, so engines are swappable via config.
- Services are pure and testable; no model loading at import time.
- Configuration through environment variables (`.env.example` documents all of them): model names and sizes, `USE_CELERY`, `DEVICE=auto|cpu|cuda`, `ENABLE_EDGE_TTS=false`, storage paths.
- Every pipeline stage updates the `jobs` table and emits a progress event.
- Errors are never silent: failures are stored, pushed to the UI, and **spoken** to the user.
- Never commit models, uploads or generated audio.
- One command to run: `make dev` (or `docker compose up`). One command to test: `make test`.

---

## 10. Build order (milestones)

1. **Scaffold:** monorepo, DB models, health endpoint, Docker Compose, README skeleton.
2. **Ingestion + extraction:** upload, PyMuPDF, DOCX, text-layer detection.
3. **OCR + language + cleanup:** Tesseract/EasyOCR, preprocessing, language detection, sentence splitting.
4. **Chapter detection:** TOC, regex (English and Urdu), heuristics, fallback.
5. **TTS:** Kokoro/Piper (English), MMS (Urdu), stitching, timing.json.
6. **Pipeline + queue:** Chapter 1 first, background rest, progress WebSocket.
7. **Translation + figure description.**
8. **STT + voice commands:** faster-whisper, VAD, intent parser, `/ws/voice`.
9. **Accessible frontend:** player, push-to-talk, spoken feedback, shortcuts.
10. **Polish:** README, demo script, seed data, end-to-end test.

---

## 11. Acceptance criteria (definition of done)

- [ ] Uploading an English digital PDF yields playable Chapter 1 audio in about 60 s on CPU.
- [ ] A scanned English PDF and a scanned Urdu PDF are OCR'd and read aloud.
- [ ] A multi-chapter book shows the correct chapter list.
- [ ] Saying "go to chapter 5" jumps to Chapter 5 and starts playing it (English and Urdu phrasing both work).
- [ ] "Forward 30 seconds" and "back 30 seconds" seek correctly, including across chapter boundaries.
- [ ] Pause, resume and stop work by voice. Speed and language switch work by voice.
- [ ] An English chapter can be played as an Urdu audio track, and the reverse.
- [ ] Closing and reopening the app resumes at the saved position.
- [ ] The whole app can be operated **without looking at the screen** (voice plus keyboard).
- [ ] At least 60 intent test phrases pass, including misrecognition-style variants.
- [ ] Runs with one command; README includes setup, model download, command list and limitations.

---

## 12. Demo script (5 minutes)

1. Upload an English textbook PDF. The app announces progress aloud.
2. Chapter 1 starts reading automatically.
3. Hold Space: "Forward thirty seconds." Then: "Go to chapter three."
4. Hold Space: "Read in Urdu." The audio switches to the Urdu track.
5. Upload a scanned Urdu page. It is OCR'd and read aloud.
6. Close the tab, reopen it, and show that it resumes at the last position.