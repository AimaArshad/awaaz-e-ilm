"""Piper TTS engine for English.

Uses the ``piper-tts`` 1.8 Python API (``PiperVoice.load`` / ``synthesize``).
The ONNX voice model is loaded lazily on first call and cached for the
process lifetime.  Models are stored under ``{MODELS_CACHE_DIR}/piper/``.

Voice: en_US-lessac-medium (configurable via ``PIPER_VOICE``).
"""
from __future__ import annotations

import io
import logging
import wave
from pathlib import Path

from pydub import AudioSegment

from app.config import get_settings
from app.services.tts.base import TTSEngine, register_engine

logger = logging.getLogger(__name__)


class PiperEnglishEngine(TTSEngine):
    """English TTS using the Piper neural TTS engine."""

    ENGINE_VERSION: str = "piper-1.8"

    def __init__(self) -> None:
        self._voice = None  # lazy-loaded PiperVoice

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _load_voice(self):
        """Load the Piper ONNX model (once)."""
        if self._voice is not None:
            return

        from piper import PiperVoice  # type: ignore[import-untyped]

        settings = get_settings()
        voice_name = settings.piper_voice  # e.g. "en_US-lessac-medium"
        models_dir = Path(settings.models_cache_dir) / "piper"

        model_path = models_dir / f"{voice_name}.onnx"
        config_path = models_dir / f"{voice_name}.onnx.json"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Piper voice model not found: {model_path}\n"
                f"Run: python scripts/download_models.py"
            )

        logger.info("Loading Piper voice from %s", model_path)
        self._voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        logger.info("Piper voice loaded: %s (sample_rate=%d)", voice_name, self._voice.config.sample_rate)

    # ------------------------------------------------------------------
    # Synthesize
    # ------------------------------------------------------------------

    def synthesize(self, text: str, lang: str = "en") -> AudioSegment:
        """Synthesise *text* and return a pydub ``AudioSegment``.

        Uses ``PiperVoice.synthesize_wav`` to write a WAV into an in-memory
        buffer, then loads it with pydub.
        """
        self._load_voice()

        text = text.strip()
        if not text:
            # Return 100ms silence for empty text
            return AudioSegment.silent(duration=100, frame_rate=self._voice.config.sample_rate)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            self._voice.synthesize_wav(text, wav_file)

        buf.seek(0)
        segment = AudioSegment.from_wav(buf)
        return segment


# Register this engine for English
register_engine("en", PiperEnglishEngine)
