"""Text preparation for TTS synthesis.

Transforms raw chapter text into clean, speakable paragraphs:

1. Drop diagram noise (low letter-ratio lines, short non-word lines).
2. Drop equation-only lines.
3. Remove figure/table references and bullet glyphs.
4. Read common symbols aloud (°C, %, m/s, m/s², units).
5. Re-join sentences broken across lines; split with pysbd.
6. Limit sentences to 300 chars (split on commas if longer).
7. Cap at AUDIO_MAX_CHARS, cutting at a sentence boundary.

All functions are pure and side-effect-free.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from app.config import get_settings
from app.services.cleanup import split_sentences

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Paragraph = List[str]  # A paragraph is a list of sentences


@dataclass
class PreparedText:
    """Result of prepare_for_speech()."""
    paragraphs: List[Paragraph]
    truncated: bool = False
    total_chars: int = 0


# ---------------------------------------------------------------------------
# Symbol pronunciation table
# ---------------------------------------------------------------------------

# Order matters: longer patterns first to avoid partial matches
_SYMBOL_TABLE: list[tuple[re.Pattern, str]] = [
    # Units with exponents
    (re.compile(r"\bm/s²\b"), "metres per second squared"),
    (re.compile(r"\bm/s\b"), "metres per second"),
    (re.compile(r"\bkm/h\b"), "kilometres per hour"),
    # Temperature
    (re.compile(r"°C\b"), " degrees Celsius"),
    (re.compile(r"°F\b"), " degrees Fahrenheit"),
    (re.compile(r"°\b"), " degrees"),
    # Percent
    (re.compile(r"%"), " percent"),
    # Units — standalone (preceded by digit or space, followed by word boundary)
    (re.compile(r"(?<=\d)\s*Hz\b"), " hertz"),
    (re.compile(r"(?<=\d)\s*kHz\b"), " kilohertz"),
    (re.compile(r"(?<=\d)\s*MHz\b"), " megahertz"),
    (re.compile(r"(?<=\d)\s*GHz\b"), " gigahertz"),
    (re.compile(r"(?<=\d)\s*kg\b"), " kilograms"),
    (re.compile(r"(?<=\d)\s*kJ\b"), " kilojoules"),
    (re.compile(r"(?<=\d)\s*kW\b"), " kilowatts"),
    (re.compile(r"(?<=\d)\s*km\b"), " kilometres"),
    (re.compile(r"(?<=\d)\s*cm\b"), " centimetres"),
    (re.compile(r"(?<=\d)\s*mm\b"), " millimetres"),
    (re.compile(r"\b(\d+)\s*N\b"), r"\1 newtons"),
    (re.compile(r"\b(\d+)\s*J\b"), r"\1 joules"),
    (re.compile(r"\b(\d+)\s*W\b"), r"\1 watts"),
    (re.compile(r"\b(\d+)\s*V\b"), r"\1 volts"),
    (re.compile(r"\b(\d+)\s*A\b"), r"\1 amperes"),
    (re.compile(r"\b(\d+)\s*m\b(?!\w)"), r"\1 metres"),
]


def _expand_symbols(text: str) -> str:
    """Replace common scientific symbols with their spoken equivalents."""
    for pattern, replacement in _SYMBOL_TABLE:
        text = pattern.sub(replacement, text)
    # Clean up double spaces introduced by replacements
    return re.sub(r"  +", " ", text)


# ---------------------------------------------------------------------------
# Noise filters
# ---------------------------------------------------------------------------

# Common short words that are legitimate single words
_REAL_SHORT_WORDS = frozenset({
    "a", "i", "an", "am", "as", "at", "be", "by", "do", "go", "he",
    "if", "in", "is", "it", "me", "my", "no", "of", "on", "or", "so",
    "to", "up", "us", "we", "the", "and", "for", "are", "but", "not",
    "you", "all", "can", "had", "her", "was", "one", "our", "out",
})

# Bare running headers that carry no content on their own
_RUNNING_HEADERS = frozenset({"chapter", "unit", "page"})

# Figure/table references: (Fig 13.1), [Fig. 2], (Table 3.1), etc.
# _FIG_TABLE_REF = re.compile(
#     r"\(?\s*(?:Fig(?:ure)?|Tab(?:le)?)\s*\.?\s*\d+(?:\.\d+)?\s*\)?",
#     re.IGNORECASE,
# )
_FIG_TABLE_REF = re.compile(
    r"\(?\s*\b(?:Fig(?:ure)?|Tab(?:le)?)\s*\.?\s*\d+(?:\.\d+)?\s*\)?",
    re.IGNORECASE,
)

# Bullet glyphs to remove
_BULLET_GLYPHS = re.compile(r"[•◦▪▸►◆■□●○@]\s*")

# Equation-only line pattern: dominated by math chars, digits, single letters
_EQUATION_RE = re.compile(
    r"^[\s\d=+\-*/^().,:;a-zA-Z]{0,200}$"
)


def _letter_ratio(line: str) -> float:
    """Ratio of letters to non-space characters in a line."""
    non_space = [c for c in line if not c.isspace()]
    if not non_space:
        return 0.0
    letters = sum(1 for c in non_space if c.isalpha())
    return letters / len(non_space)


def _is_diagram_noise(line: str) -> bool:
    """True if the line is likely diagram/table noise."""
    stripped = line.strip()
    if not stripped:
        return True

    # Low letter ratio → noise
    if _letter_ratio(stripped) < 0.60:
        return True

    # Short lines (< 3 letters) that aren't real words.
    # isalpha() counts Urdu letters too, so Urdu lines are not dropped.
    letters_only = "".join(c for c in stripped if c.isalpha())
    if len(letters_only) < 3:
        if stripped.lower() not in _REAL_SHORT_WORDS:
            return True

    # Bare running header such as "chapter" or "| chapter |"
    if stripped.lower().strip(" |.:-") in _RUNNING_HEADERS:
        return True

    # OCR garble: one token with 2+ lowercase->uppercase jumps ("ToneEenmE")
    tokens = stripped.split()
    if len(tokens) == 1 and len(re.findall(r"[a-z][A-Z]", tokens[0])) >= 2:
        return True

    # Lines with | or @ and fewer than 4 words are table/diagram debris
    if "|" in stripped or "@" in stripped:
        if len(re.findall(r"[^\W\d_]+", stripped)) < 4:
            return True

    return False


def _is_equation_line(line: str) -> bool:
    """True if the line is dominated by equation characters."""
    stripped = line.strip()
    if not stripped:
        return False

    # Count math-like characters: digits, operators, single-letter variables
    math_chars = sum(
        1 for c in stripped
        if c in "0123456789=+-*/^().," or (c.isspace())
    )
    non_space = [c for c in stripped if not c.isspace()]
    if not non_space:
        return False

    # Check if words are mostly single characters (variable names)
    words = re.findall(r"[a-zA-Z]+", stripped)
    long_words = [w for w in words if len(w) > 2]

    # If most of the line is math chars + single-letter words
    alpha_chars = sum(len(w) for w in words)
    total_non_space = len(non_space)

    if total_non_space == 0:
        return False

    math_ratio = (math_chars + alpha_chars) / total_non_space
    if math_ratio > 0.85 and not long_words:
        return True

    # Specific patterns: "ma=-kx", "KE. = 1/2 mv2", "F = ma"
    if re.match(r"^[a-zA-Z]{1,3}\.?\s*=\s*.*$", stripped) and len(stripped) < 50:
        if not long_words:
            return True

    return False


def _clean_line(line: str) -> str:
    """Clean a single line: remove refs, bullets, expand symbols."""
    line = _FIG_TABLE_REF.sub(" ", line)           # leave one space, not zero
    line = _BULLET_GLYPHS.sub("", line)
    line = re.sub(r"\s+", " ", line)                # collapse whitespace
    line = re.sub(r"\s+([.,;:!?])", r"\1", line)    # "shown ." -> "shown."
    line = _expand_symbols(line)
    return line.strip()


# ---------------------------------------------------------------------------
# Sentence length limiting
# ---------------------------------------------------------------------------

_MAX_SENTENCE_CHARS = 300


def _split_long_sentence(sentence: str, max_chars: int = _MAX_SENTENCE_CHARS) -> list[str]:
    """Split a sentence longer than max_chars on commas."""
    if len(sentence) <= max_chars:
        return [sentence]

    # Split on commas
    parts = sentence.split(",")
    result: list[str] = []
    current = ""

    for part in parts:
        candidate = f"{current}, {part.strip()}" if current else part.strip()
        if len(candidate) > max_chars and current:
            result.append(current.strip())
            current = part.strip()
        else:
            current = candidate

    if current.strip():
        result.append(current.strip())

    # If we still have chunks that are too long, hard-split them
    final: list[str] = []
    for chunk in result:
        if len(chunk) > max_chars:
            # Hard split at max_chars on word boundary
            while len(chunk) > max_chars:
                split_at = chunk[:max_chars].rfind(" ")
                if split_at <= 0:
                    split_at = max_chars
                final.append(chunk[:split_at].strip())
                chunk = chunk[split_at:].strip()
            if chunk:
                final.append(chunk)
        else:
            final.append(chunk)

    return [s for s in final if s.strip()]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def prepare_for_speech(text: str, lang: str = "en") -> PreparedText:
    """Prepare chapter text for TTS synthesis.

    Args:
        text: Raw chapter text.
        lang: Language code.

    Returns:
        ``PreparedText`` with a list of paragraphs (each a list of sentences),
        a ``truncated`` flag, and ``total_chars`` count.
    """
    settings = get_settings()
    max_chars = settings.audio_max_chars

    # Split into raw paragraphs (double newline)
    raw_paragraphs = re.split(r"\n\s*\n", text)

    paragraphs: list[Paragraph] = []
    char_count = 0
    truncated = False

    for raw_para in raw_paragraphs:
        lines = raw_para.split("\n")

        # Filter noise lines
        clean_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _is_diagram_noise(stripped):
                continue
            if _is_equation_line(stripped):
                continue
            cleaned = _clean_line(stripped)
            if cleaned:
                clean_lines.append(cleaned)

        if not clean_lines:
            continue

        # Re-join lines into flowing text (fix line-break mid-sentence)
        joined = " ".join(clean_lines)
        # Collapse multiple spaces
        joined = re.sub(r"\s+", " ", joined).strip()

        # Sentence splitting using pysbd (via cleanup.py)
        sentences = split_sentences(joined, lang=lang)

        # Limit sentence length
        limited: list[str] = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            limited.extend(_split_long_sentence(sent))

        if not limited:
            continue

        # Check char cap
        para_sentences: list[str] = []
        for sent in limited:
            if char_count + len(sent) > max_chars:
                truncated = True
                break
            para_sentences.append(sent)
            char_count += len(sent)

        if para_sentences:
            paragraphs.append(para_sentences)

        if truncated:
            break

    return PreparedText(
        paragraphs=paragraphs,
        truncated=truncated,
        total_chars=char_count,
    )