"""Speech-to-text using faster-whisper (lazy-loaded, thread-offloaded)."""
from __future__ import annotations

import asyncio
import logging
import threading

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
_infer_lock = threading.Lock()

# Biases Whisper towards our command vocabulary (helps short utterances).
_COMMAND_PROMPT = (
    "Voice commands for an audiobook player: go to chapter five, "
    "play the topic on photosynthesis, forward thirty seconds, pause, resume."
)


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel

        s = get_settings()
        device, compute = ("cuda", "float16") if s.device == "cuda" else ("cpu", "int8")
        logger.info("Loading Whisper '%s' (device=%s, compute=%s)", s.whisper_model, device, compute)
        _model = WhisperModel(s.whisper_model, device=device, compute_type=compute,
                              download_root=s.models_cache_dir)
        logger.info("Whisper model ready.")
    return _model


def preload() -> None:
    """Call at startup (in a thread) so the first command isn't slow."""
    try:
        _get_model()
    except Exception:
        logger.exception("Whisper preload failed (will retry on first use)")


def _transcribe_sync(audio_np: np.ndarray, lang: str | None) -> dict:
    model = _get_model()
    with _infer_lock:
        segments, info = model.transcribe(
            audio_np,
            language=lang,
            beam_size=3,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=_COMMAND_PROMPT if lang in (None, "en") else None,
        )
        seg_list = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    text = " ".join(s["text"] for s in seg_list if s["text"]).strip()
    logger.info("Whisper: '%s' (lang=%s)", text, info.language)
    return {"text": text, "language": info.language, "segments": seg_list}


async def transcribe(audio_bytes: bytes, lang: str | None = None) -> dict:
    """Transcribe raw little-endian int16 mono PCM at 16 kHz."""
    if not audio_bytes or len(audio_bytes) < 3200:  # < 100 ms
        return {"text": "", "language": lang or "en", "segments": []}
    audio_np = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0
    return await asyncio.to_thread(_transcribe_sync, audio_np, lang)




# # """Speech-to-text service using OpenAI Whisper.

# # Milestone 4 implementation plan
# # --------------------------------
# # - Load `whisper.load_model(settings.whisper_model)` once at startup.
# # - Accept raw PCM audio bytes (16 kHz, 16-bit mono).
# # - Convert bytes → numpy float32 array.
# # - Run `model.transcribe(audio, language=lang, task="transcribe")`.
# # - Return transcript string and detected language code.

# # Supported languages: "en", "ur" (Whisper medium or large for best Urdu accuracy).
# # """
# # from __future__ import annotations


# # async def transcribe(audio_bytes: bytes, lang: str | None = None) -> dict:
# #     """Transcribe audio bytes to text using Whisper.

# #     Args:
# #         audio_bytes: Raw PCM audio (16 kHz, 16-bit mono).
# #         lang: Hint language code or None for auto-detection.

# #     Returns:
# #         Dict with keys: "text" (str), "language" (str), "segments" (list).

# #     TODO (Milestone 4):
# #         - Import whisper: `import whisper`
# #         - Decode PCM bytes to numpy: `np.frombuffer(audio_bytes, np.int16) / 32768.0`
# #         - Call `model.transcribe(audio_np, language=lang)`
# #     """
# #     raise NotImplementedError("STT coming in Milestone 4.")


# """Speech-to-text service using faster-whisper.

# Loads the model lazily on first call and caches it for the process lifetime.
# """
# from __future__ import annotations

# import logging
# import threading

# import numpy as np

# from app.config import get_settings

# logger = logging.getLogger(__name__)

# _model = None
# _model_lock = threading.Lock()


# def _get_model():
#     """Load the faster-whisper model once (thread-safe)."""
#     global _model
#     if _model is not None:
#         return _model

#     with _model_lock:
#         if _model is not None:
#             return _model

#         from faster_whisper import WhisperModel

#         settings = get_settings()
#         # On CPU, int8 is much faster and uses less RAM
#         if settings.device == "cuda":
#             device, compute_type = "cuda", "float16"
#         else:
#             device, compute_type = "cpu", "int8"

#         logger.info(
#             "Loading Whisper model '%s' (device=%s, compute=%s)",
#             settings.whisper_model, device, compute_type,
#         )
#         _model = WhisperModel(
#             settings.whisper_model,
#             device=device,
#             compute_type=compute_type,
#             download_root=settings.models_cache_dir,
#         )
#         logger.info("Whisper model ready.")
#     return _model


# async def transcribe(audio_bytes: bytes, lang: str | None = None) -> dict:
#     """Transcribe raw 16-bit mono PCM at 16 kHz.

#     Args:
#         audio_bytes: Raw little-endian int16 PCM.
#         lang: Optional language hint ("en", "ur"); None = auto-detect.

#     Returns:
#         {"text": str, "language": str, "segments": list[dict]}
#     """
#     if not audio_bytes or len(audio_bytes) < 3200:  # <100 ms → skip
#         return {"text": "", "language": lang or "en", "segments": []}

#     model = _get_model()
#     audio_np = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0

#     segments, info = model.transcribe(
#         audio_np,
#         language=lang,
#         beam_size=5,
#         vad_filter=True,
#     )

#     text_parts = []
#     segment_list = []
#     for seg in segments:
#         text_parts.append(seg.text.strip())
#         segment_list.append(
#             {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
#         )

#     full_text = " ".join(p for p in text_parts if p).strip()
#     logger.info("Whisper: '%s' (lang=%s)", full_text, info.language)

#     return {"text": full_text, "language": info.language, "segments": segment_list}