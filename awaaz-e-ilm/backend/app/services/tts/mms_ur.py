"""MMS (Massively Multilingual Speech) TTS engine for Urdu.

Milestone 3 implementation plan
--------------------------------
Facebook MMS supports 1,100+ languages including Urdu (urd).
- Model: facebook/mms-tts-urd
- Load: `VitsModel.from_pretrained("facebook/mms-tts-urd")`
- Tokenise: `AutoTokenizer.from_pretrained("facebook/mms-tts-urd")`
- Synthesise: `model.generate(**inputs)` → waveform tensor.
- Convert tensor to WAV bytes via scipy or soundfile.

Quality note: MMS Urdu is intelligible but less natural than English voices.
Consider edge-tts as an online fallback if `enable_edge_tts=true`.
"""
from __future__ import annotations

from app.services.tts.base import TTSBase


class MMSUrduTTS(TTSBase):
    """Urdu TTS using Facebook's MMS (Massively Multilingual Speech) model.

    TODO (Milestone 3):
        - Install: `pip install transformers soundfile scipy`
        - Load VitsModel and AutoTokenizer from HuggingFace.
        - Implement synthesize() with batched inference.
        - Optionally wrap edge-tts as a higher-quality online fallback.
    """

    MODEL_ID = "facebook/mms-tts-urd"

    async def synthesize(
        self,
        text: str,
        lang: str = "ur",
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesise Urdu text with MMS.

        Returns WAV bytes.
        """
        raise NotImplementedError("MMS Urdu TTS coming in Milestone 3.")


def get_tts() -> MMSUrduTTS:
    """Return the MMSUrduTTS singleton."""
    return MMSUrduTTS()
