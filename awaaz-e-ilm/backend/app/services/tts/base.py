"""Abstract base class and registry for TTS engines.

Every TTS engine (Piper, Kokoro, MMS, etc.) must subclass ``TTSEngine``.
Engines are registered in ``_REGISTRY`` and retrieved via ``get_engine(lang)``.
Models are loaded lazily on first use and cached for the process lifetime.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Type

from pydub import AudioSegment


class TTSEngine(ABC):
    """Abstract TTS engine.

    Subclasses synthesise speech for a specific language / engine combination.
    ``synthesize`` is a *synchronous* method so it can run in a thread-pool
    without needing an event loop.
    """

    # Overridden by each subclass
    ENGINE_VERSION: str = "0.0"

    @abstractmethod
    def synthesize(self, text: str, lang: str = "en") -> AudioSegment:
        """Synthesise speech for *text* and return a pydub ``AudioSegment``.

        Args:
            text: Input text to speak (single sentence preferred).
            lang: BCP-47 language code (e.g. ``"en"``).

        Returns:
            ``AudioSegment`` with the rendered speech (16-bit PCM, mono).
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable engine name."""
        return self.__class__.__name__


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Maps language code -> TTSEngine subclass
_REGISTRY: Dict[str, Type[TTSEngine]] = {}

# Cached singleton instances (lazy-loaded)
_INSTANCES: Dict[str, TTSEngine] = {}


def register_engine(lang: str, cls: Type[TTSEngine]) -> None:
    """Register a TTSEngine subclass for a language."""
    _REGISTRY[lang] = cls


def get_engine(lang: str) -> TTSEngine:
    """Return a (cached) TTSEngine instance for *lang*.

    Raises ``KeyError`` if no engine is registered for the language.
    """
    if lang not in _INSTANCES:
        if lang not in _REGISTRY:
            raise KeyError(f"No TTS engine registered for language '{lang}'")
        _INSTANCES[lang] = _REGISTRY[lang]()
    return _INSTANCES[lang]


def reset_engines() -> None:
    """Clear all cached engine instances (useful for testing)."""
    _INSTANCES.clear()
