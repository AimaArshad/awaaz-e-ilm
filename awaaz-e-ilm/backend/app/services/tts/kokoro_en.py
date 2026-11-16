"""Kokoro TTS engine for English.

Milestone 3 implementation plan
--------------------------------
Kokoro is a lightweight high-quality English TTS model.
- Load model once: `from kokoro import KPipeline; pipeline = KPipeline(lang_code="a")`
- Synthesise: `generator = pipeline(text, voice=voice, speed=speed)`
- Collect audio chunks and concatenate.
- Return WAV bytes via `soundfile` or `scipy.io.wavfile`.

Voices: "af_heart" (default female), "am_adam" (male), etc.
"""
from __future__ import annotations

from app.services.tts.base import TTSBase


class KokoroTTS(TTSBase):
    """High-quality English TTS using the Kokoro model.

    TODO (Milestone 3):
        - Install: `pip install kokoro soundfile`
        - Import and initialise KPipeline at first call.
        - Implement synthesize() using the KPipeline generator.
    """

    DEFAULT_VOICE = "af_heart"

    async def synthesize(
        self,
        text: str,
        lang: str = "en",
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesise English text with Kokoro.

        Returns WAV bytes.
        """
        raise NotImplementedError("Kokoro TTS coming in Milestone 3.")


def get_tts() -> KokoroTTS:
    """Return the KokoroTTS singleton."""
    return KokoroTTS()
