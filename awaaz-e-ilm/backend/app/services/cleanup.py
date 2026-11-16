"""Text cleanup and normalisation service.

Transforms raw extracted / OCR'd text into clean, TTS-ready content.

Pipeline
--------
1. **Unicode normalisation** — NFC for Arabic/Urdu, NFKC for Latin.
2. **Urdu-specific normalisation** — canonical forms for ی / ک / ہ / ە.
3. **Control-character removal**.
4. **Header / footer / page-number removal** — heuristic patterns.
5. **Hyphenation repair** — rejoin words split across PDF line breaks.
6. **Whitespace collapse**.
7. **Sentence splitting** — via ``pysbd`` for EN and UR.

All functions are pure and side-effect-free.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List


# ---------------------------------------------------------------------------
# 1. Unicode normalisation
# ---------------------------------------------------------------------------

def normalize_unicode(text: str, lang: str = "en") -> str:
    """Apply the appropriate Unicode normalisation form.

    - Arabic / Urdu  → NFC  (preserves composed characters).
    - Latin / other  → NFKC (compatibility decomposition + composition).
    """
    form = "NFC" if lang in ("ur", "ar") else "NFKC"
    return unicodedata.normalize(form, text)


# ---------------------------------------------------------------------------
# 2. Urdu-specific character normalisation
# ---------------------------------------------------------------------------

# Common variant mappings for Urdu text
_URDU_CHAR_MAP = {
    "\u064A": "\u06CC",  # Arabic Ya  ي → Urdu Ya  ی
    "\u0643": "\u06A9",  # Arabic Kaf ك → Urdu Kaf ک
    "\u0647": "\u06C1",  # Arabic Ha  ه → Urdu Ha  ہ  (context-dependent)
    "\u06BE": "\u06C1",  # Urdu Do-Chashmi He ھ → Ha ہ  (optional, depends on convention)
    "\u0649": "\u06CC",  # Alef Maksura ى → Urdu Ya ی
}

# Build a translation table for str.translate (fast)
_URDU_TRANS_TABLE = str.maketrans(_URDU_CHAR_MAP)


def normalize_urdu(text: str) -> str:
    """Normalise Urdu-specific character variants to their canonical forms.

    Replaces Arabic-form ي / ك / ه with their Urdu equivalents ی / ک / ہ
    and normalises Unicode.
    """
    text = text.translate(_URDU_TRANS_TABLE)
    # Remove tatweel (kashida) used for justification in Arabic typesetting
    text = text.replace("\u0640", "")
    # Normalise zero-width non-joiner / joiner (keep them — they're meaningful in Urdu)
    return text


# ---------------------------------------------------------------------------
# 3. Control-character removal
# ---------------------------------------------------------------------------

def remove_control_chars(text: str) -> str:
    """Remove ASCII control characters except ``\\n``, ``\\r``, ``\\t``."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


# ---------------------------------------------------------------------------
# 4. Header / footer / page-number removal
# ---------------------------------------------------------------------------

# Patterns that typically match page numbers (standalone lines)
_PAGE_NUMBER_RE = re.compile(
    r"^\s*"
    r"(?:"
    r"(?:page\s*)?\d{1,4}"       # "Page 12" or just "12"
    r"|[-–—]\s*\d{1,4}\s*[-–—]"  # "— 12 —"
    r"|[\u0660-\u0669]{1,4}"     # Eastern Arabic numerals ٠١٢...
    r")"
    r"\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Common header / footer patterns (repeated document title, "Copyright …", etc.)
_HEADER_FOOTER_PATTERNS = [
    re.compile(r"^\s*copyright\s.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*all rights reserved\.?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*confidential\s*$", re.IGNORECASE | re.MULTILINE),
]


def remove_headers_footers(text: str) -> str:
    """Remove likely page numbers, copyright lines, and other boilerplate.

    This is a heuristic — it may occasionally remove legitimate content.
    """
    text = _PAGE_NUMBER_RE.sub("", text)
    for pattern in _HEADER_FOOTER_PATTERNS:
        text = pattern.sub("", text)
    return text


# ---------------------------------------------------------------------------
# 5. Hyphenation repair
# ---------------------------------------------------------------------------

def fix_hyphenation(text: str) -> str:
    """Rejoin words broken by end-of-line hyphenation in PDFs.

    ``"knowl-\\nedge"`` → ``"knowledge"``
    """
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


# ---------------------------------------------------------------------------
# 6. Whitespace collapse
# ---------------------------------------------------------------------------

def collapse_whitespace(text: str) -> str:
    """Collapse runs of ≥ 3 blank lines to 2 and strip trailing spaces."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


# ---------------------------------------------------------------------------
# 7. Sentence splitting  (pysbd)
# ---------------------------------------------------------------------------

# Lazy singleton segmenters
_segmenters: dict[str, object] = {}


def _get_segmenter(lang: str):
    """Return a cached ``pysbd.Segmenter`` for the given language."""
    if lang not in _segmenters:
        try:
            import pysbd
            # pysbd supports "en" natively; "ur" falls back to "en" rules
            seg_lang = lang if lang in ("en", "es", "de", "fr", "it", "nl", "pl", "ru", "zh") else "en"
            _segmenters[lang] = pysbd.Segmenter(language=seg_lang, clean=False)
        except ImportError:
            _segmenters[lang] = None
    return _segmenters[lang]


def split_sentences(text: str, lang: str = "en") -> List[str]:
    """Split text into sentences using pysbd.

    Falls back to a simple regex splitter if pysbd is not installed.

    Args:
        text: Input text.
        lang: Language code (``"en"`` or ``"ur"``).

    Returns:
        List of sentence strings.
    """
    segmenter = _get_segmenter(lang)
    if segmenter is not None:
        return segmenter.segment(text)

    # Fallback: split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?۔।])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Public API — full cleanup pipeline
# ---------------------------------------------------------------------------

def clean_text(text: str, lang: str = "en") -> str:
    """Run the full cleanup pipeline on extracted text.

    Steps (in order):
        1. Unicode normalisation
        2. Urdu character normalisation (if lang == "ur")
        3. Control-character removal
        4. Header / footer / page-number removal
        5. Hyphenation repair
        6. Whitespace collapse

    Args:
        text: Raw extracted text.
        lang: Language code for language-specific rules.

    Returns:
        Cleaned text ready for chapter splitting and TTS.
    """
    text = normalize_unicode(text, lang)

    if lang == "ur":
        text = normalize_urdu(text)

    text = remove_control_chars(text)
    text = remove_headers_footers(text)
    text = fix_hyphenation(text)
    text = collapse_whitespace(text)

    return text
