# AI Models and Licenses

This document lists all AI models used in Awaaz-e-Ilm, their sources, and their licenses.

## Speech-to-Text (STT)

| Model | Source | License | Notes |
|-------|--------|---------|-------|
| Whisper `tiny` | OpenAI | MIT | Fastest, lowest accuracy |
| Whisper `base` | OpenAI | MIT | Good balance for English |
| Whisper `small` | OpenAI | MIT | **Default** — balanced accuracy/speed |
| Whisper `medium` | OpenAI | MIT | Better Urdu accuracy |
| Whisper `large-v3` | OpenAI | MIT | Best accuracy; requires GPU |

HuggingFace: `openai/whisper-{size}`

## Text-to-Speech (TTS) — English

| Model | Source | License | Notes |
|-------|--------|---------|-------|
| Kokoro TTS | HuggingFace | Apache 2.0 | High-quality, 500M params |
| Piper TTS | rhasspy | MIT | Offline, fast, many voices |

Kokoro HuggingFace: `hexgrad/Kokoro-82M`
Piper voices: `rhasspy/piper-voices`

## Text-to-Speech (TTS) — Urdu

| Model | Source | License | Notes |
|-------|--------|---------|-------|
| MMS TTS Urdu | Meta AI | CC-BY-NC 4.0 | Offline, 1100+ languages |
| Edge TTS (ur-PK) | Microsoft | Proprietary (online) | Optional fallback; requires internet |

MMS HuggingFace: `facebook/mms-tts-urd`

> **Note**: MMS is released under CC-BY-NC 4.0, which restricts commercial use.
> For commercial deployment, use an alternative Urdu TTS or obtain a license.

## Image Captioning / Vision

| Model | Source | License | Notes |
|-------|--------|---------|-------|
| Florence-2-base | Microsoft | MIT | Image captioning for accessibility |

HuggingFace: `microsoft/Florence-2-base`

## Machine Translation

| Model | Source | License | Notes |
|-------|--------|---------|-------|
| opus-mt-en-ur | Helsinki-NLP | CC-BY 4.0 | English → Urdu |
| opus-mt-ur-en | Helsinki-NLP | CC-BY 4.0 | Urdu → English |

HuggingFace: `Helsinki-NLP/opus-mt-en-ur`, `Helsinki-NLP/opus-mt-ur-en`

## Voice Activity Detection

| Model | Source | License | Notes |
|-------|--------|---------|-------|
| Silero VAD | snakers4 | MIT | Lightweight, real-time VAD |

GitHub: `snakers4/silero-vad`

## Summary Table

| Component | Model | License | Commercial Use |
|-----------|-------|---------|---------------|
| ASR | Whisper | MIT | ✅ |
| TTS (en) | Kokoro | Apache 2.0 | ✅ |
| TTS (en alt) | Piper | MIT | ✅ |
| TTS (ur) | MMS | CC-BY-NC 4.0 | ❌ |
| Vision | Florence-2 | MIT | ✅ |
| Translation | MarianMT | CC-BY 4.0 | ✅ |
| VAD | Silero | MIT | ✅ |
