"""Speech-to-text service using OpenAI Whisper.

Milestone 4 implementation plan
--------------------------------
- Load `whisper.load_model(settings.whisper_model)` once at startup.
- Accept raw PCM audio bytes (16 kHz, 16-bit mono).
- Convert bytes → numpy float32 array.
- Run `model.transcribe(audio, language=lang, task="transcribe")`.
- Return transcript string and detected language code.

Supported languages: "en", "ur" (Whisper medium or large for best Urdu accuracy).
"""
from __future__ import annotations


async def transcribe(audio_bytes: bytes, lang: str | None = None) -> dict:
    """Transcribe audio bytes to text using Whisper.

    Args:
        audio_bytes: Raw PCM audio (16 kHz, 16-bit mono).
        lang: Hint language code or None for auto-detection.

    Returns:
        Dict with keys: "text" (str), "language" (str), "segments" (list).

    TODO (Milestone 4):
        - Import whisper: `import whisper`
        - Decode PCM bytes to numpy: `np.frombuffer(audio_bytes, np.int16) / 32768.0`
        - Call `model.transcribe(audio_np, language=lang)`
    """
    raise NotImplementedError("STT coming in Milestone 4.")
