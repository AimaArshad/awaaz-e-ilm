"""Machine translation service (English ↔ Urdu).

Milestone 3 implementation plan
--------------------------------
Uses Helsinki-NLP MarianMT models:
- opus-mt-en-ur  (English → Urdu)
- opus-mt-ur-en  (Urdu → English)

Models are loaded lazily on first call and cached as module-level singletons
to avoid reloading on every request.

Sentence splitting uses `nltk.sent_tokenize` to avoid exceeding model max length.
"""
from __future__ import annotations


async def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    """Translate text between English and Urdu.

    Args:
        text: Source text to translate.
        src_lang: BCP-47 source language code ("en" or "ur").
        tgt_lang: BCP-47 target language code ("en" or "ur").

    Returns:
        Translated text string.

    TODO (Milestone 3):
        - Load MarianMTModel and MarianTokenizer from HuggingFace.
        - Split text into sentences.
        - Batch-translate in chunks of 32 sentences.
        - Reconstruct and return joined translated text.
    """
    raise NotImplementedError("Translation coming in Milestone 3.")
