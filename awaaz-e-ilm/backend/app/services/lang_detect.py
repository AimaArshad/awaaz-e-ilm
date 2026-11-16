"""Language detection service.

Uses a two-stage approach per the architecture:
  1. **Arabic-script ratio** — fast heuristic based on Unicode code-point
     ranges.  If the ratio of Arabic-script characters exceeds the threshold
     the text is classified as Urdu.
  2. **lingua** — statistical confirmation for borderline cases.

The public entry point is :func:`detect_language` (single text) and
:func:`detect_paragraphs` (per-paragraph breakdown).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unicode ranges for Arabic / Urdu script
# ---------------------------------------------------------------------------
# Arabic           \u0600–\u06FF
# Arabic Supplement \u0750–\u077F
# Arabic Extended-A \u08A0–\u08FF
# Arabic Pres. A    \uFB50–\uFDFF
# Arabic Pres. B    \uFE70–\uFEFF
_ARABIC_SCRIPT_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
_LATIN_SCRIPT_RE = re.compile(r"[A-Za-z]")

# Threshold above which we consider the text Urdu
_ARABIC_RATIO_THRESHOLD = 0.30

# Minimum characters needed for a reliable detection
_MIN_CHARS_FOR_DETECTION = 10


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LangSpan:
    """A contiguous span of text in a single language."""
    text: str
    lang: str            # "en" or "ur"
    confidence: float    # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Arabic-script ratio (fast path)
# ---------------------------------------------------------------------------

def arabic_script_ratio(text: str) -> float:
    """Return the fraction of alphabetic characters that are Arabic-script.

    Non-letter characters (digits, punctuation, whitespace) are ignored.

    Returns:
        A float in [0.0, 1.0].  1.0 means every letter is Arabic-script.
    """
    arabic_count = len(_ARABIC_SCRIPT_RE.findall(text))
    latin_count = len(_LATIN_SCRIPT_RE.findall(text))
    total = arabic_count + latin_count
    if total == 0:
        return 0.0
    return arabic_count / total


# ---------------------------------------------------------------------------
# lingua-based detection (accurate path)
# ---------------------------------------------------------------------------

# Lazy singleton — importing lingua is slow (~200 ms)
_lingua_detector = None


def _get_lingua_detector():
    """Create or return a cached lingua LanguageDetector."""
    global _lingua_detector
    if _lingua_detector is None:
        try:
            from lingua import Language, LanguageDetectorBuilder
            _lingua_detector = (
                LanguageDetectorBuilder
                .from_languages(Language.ENGLISH, Language.URDU)
                .with_preloaded_language_models()
                .build()
            )
            logger.info("lingua detector initialised (en, ur)")
        except ImportError:
            logger.warning(
                "lingua-language-detector not installed — "
                "falling back to script-ratio only"
            )
            _lingua_detector = False  # sentinel: tried and failed
    return _lingua_detector if _lingua_detector is not False else None


def _detect_with_lingua(text: str) -> Optional[str]:
    """Detect language using lingua.  Returns ``"en"`` or ``"ur"`` or *None*."""
    det = _get_lingua_detector()
    if det is None:
        return None
    try:
        from lingua import Language
        result = det.detect_language_of(text)
        if result == Language.URDU:
            return "ur"
        if result == Language.ENGLISH:
            return "en"
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_language(text: str, default: str = "en") -> str:
    """Detect the primary language of a text snippet.

    Strategy:
        1. If the Arabic-script ratio ≥ threshold → ``"ur"``.
        2. Otherwise ask lingua for confirmation.
        3. Fall back to *default* if inconclusive.

    Args:
        text:    Input text (≥ ~50 characters for reliable results).
        default: Language code returned when detection is inconclusive.

    Returns:
        ``"en"`` or ``"ur"``.
    """
    clean = text.strip()
    if len(clean) < _MIN_CHARS_FOR_DETECTION:
        return default

    ratio = arabic_script_ratio(clean)

    if ratio >= _ARABIC_RATIO_THRESHOLD:
        return "ur"
    if ratio <= 0.05:
        return "en"

    # Borderline — use lingua for confirmation
    lingua_result = _detect_with_lingua(clean)
    if lingua_result:
        return lingua_result

    return default


def detect_paragraphs(text: str, default: str = "en") -> List[LangSpan]:
    """Split text into paragraphs and detect the language of each.

    Paragraphs are delimited by one or more blank lines.

    Args:
        text:    Full document text.
        default: Fallback language code.

    Returns:
        A list of :class:`LangSpan` objects, one per paragraph.
    """
    # Split on blank lines
    paragraphs = re.split(r"\n\s*\n", text.strip())
    spans: List[LangSpan] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lang = detect_language(para, default=default)
        ratio = arabic_script_ratio(para)
        # Confidence heuristic: distance from the decision boundary
        if lang == "ur":
            conf = min(1.0, ratio / _ARABIC_RATIO_THRESHOLD)
        else:
            conf = min(1.0, (1 - ratio) / (1 - _ARABIC_RATIO_THRESHOLD))

        spans.append(LangSpan(text=para, lang=lang, confidence=round(conf, 3)))

    return spans
