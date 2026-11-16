# Awaaz-e-Ilm — 5-Minute Demo Script

This script guides a live demonstration of the Awaaz-e-Ilm platform to judges, supervisors, or users.

---

## Setup (before the demo)

- [ ] Backend running: `uvicorn app.main:app --reload` (port 8000)
- [ ] Frontend running: `npm run dev` (port 5173)
- [ ] Demo PDF ready: `scripts/fixtures/sample_chapter.pdf` (English + images)
- [ ] Microphone configured and tested
- [ ] Screen magnification or high-contrast mode enabled (optional)

---

## Minute 1: Introduction (60s)

> "Awaaz-e-Ilm — meaning 'Voice of Knowledge' — is a voice-controlled audiobook platform
> designed specifically for visually impaired students in Pakistan.
> It converts any PDF, EPUB, or scanned textbook into a fully spoken, navigable audiobook
> that works in both English and Urdu."

**Show:** Home screen with keyboard-first UI.

---

## Minute 2: Upload a Document (60s)

1. Navigate to Upload page (or press **U**).
2. Drag and drop `sample_chapter.pdf` onto the drop zone.
3. Set title: "Introduction to Computer Science".
4. Click **Upload Book**.

**Narrate:**
> "The system accepts PDF, EPUB, TXT, and even scanned images.
> It automatically extracts text, detects the language, and splits the content into chapters."

**Show:** Processing progress bar; switch to Player page once ready.

---

## Minute 3: Audio Playback and Navigation (60s)

1. Click **Play** (or press **K**).
2. Demonstrate playback at 1.0×, then switch to 1.5×.
3. Press **L** to skip forward 30 seconds.
4. Press **J** to go back 30 seconds.
5. Click Chapter 2 in the sidebar (or press **N**).

**Narrate:**
> "All controls work with keyboard shortcuts.
> The transcript highlights in sync with the audio.
> Students can navigate by chapter, seek by seconds, or change speed."

---

## Minute 4: Voice Commands (60s)

1. Hold **Space** to activate push-to-talk.
2. Say: **"Go to chapter three"**
   - System navigates to chapter 3 and announces it.
3. Say: **"Forward thirty seconds"**
   - Audio seeks forward.
4. Say: **"Read in Urdu"**
   - Audio switches to Urdu TTS.
5. Say (in Urdu): **"رکو"** ("Stop")
   - Audio pauses.

**Narrate:**
> "Voice commands work in English, Urdu, and Roman Urdu.
> The system uses Whisper for transcription and a rule-based intent parser
> optimised for accessibility commands."

---

## Minute 5: Settings and Accessibility (60s)

1. Navigate to Settings (or press **?** → Settings).
2. Toggle **High Contrast Mode** on.
3. Change playback speed to **1.5×**.
4. Switch TTS engine to **Piper** (English).
5. Change Whisper model to **medium** for better Urdu accuracy.

**Narrate:**
> "The platform stores preferences locally.
> High-contrast mode ensures readability for low-vision users.
> All UI elements are keyboard accessible and announce state to screen readers."

---

## Q&A Prep

**Q: What languages are supported?**
A: English and Urdu for TTS. ASR (Whisper) supports both; Urdu accuracy is best with the medium or large model.

**Q: Does it work offline?**
A: Yes — Whisper, Kokoro (English TTS), MMS (Urdu TTS), and translation models all run locally.

**Q: What about Urdu OCR?**
A: Nastaliq-script OCR is challenging. We use Tesseract with Urdu language packs and EasyOCR as a fallback. Accuracy is lower for low-quality scans.

**Q: What is the hardware requirement?**
A: Minimum 8 GB RAM, 4-core CPU. GPU (NVIDIA with CUDA) recommended for Whisper medium/large.
