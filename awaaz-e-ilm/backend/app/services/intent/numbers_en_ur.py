"""Word-to-number converter for English, Urdu, and Roman Urdu.

Used by the intent parser to convert spoken number words to integers.

Examples
--------
English:   "five"       → 5
           "thirty"     → 30
           "forty two"  → 42
Urdu:      "پانچ"       → 5
           "تیس"        → 30
Roman Urdu:"paanch"     → 5
           "tees"       → 30
"""
from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# English word → integer maps
# ---------------------------------------------------------------------------
_EN_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_EN_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# ---------------------------------------------------------------------------
# Urdu (native script) → integer maps
# ---------------------------------------------------------------------------
_UR_ONES = {
    "صفر": 0, "ایک": 1, "دو": 2, "تین": 3, "چار": 4, "پانچ": 5,
    "چھ": 6, "سات": 7, "آٹھ": 8, "نو": 9, "دس": 10,
    "گیارہ": 11, "بارہ": 12, "تیرہ": 13, "چودہ": 14, "پندرہ": 15,
    "سولہ": 16, "سترہ": 17, "اٹھارہ": 18, "انیس": 19,
}
_UR_TENS = {
    "بیس": 20, "تیس": 30, "چالیس": 40, "پچاس": 50,
    "ساٹھ": 60, "ستر": 70, "اسی": 80, "نوے": 90,
}

# ---------------------------------------------------------------------------
# Roman Urdu (Latin transliteration) → integer maps
# ---------------------------------------------------------------------------
_RU_ONES = {
    "sifar": 0, "aik": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
    "chay": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unees": 19,
}
_RU_TENS = {
    "bees": 20, "tees": 30, "chalees": 40, "pachaas": 50,
    "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
}


def word_to_number(text: str) -> int | None:
    """Convert a spoken number (English, Urdu, or Roman Urdu) to an integer.

    Args:
        text: A word or short phrase representing a number.

    Returns:
        Integer value, or None if conversion fails.

    Examples:
        >>> word_to_number("thirty")
        30
        >>> word_to_number("تیس")
        30
        >>> word_to_number("tees")
        30
        >>> word_to_number("42")
        42
    """
    text = text.strip().lower()

    # Already a digit string
    if re.match(r"^\d+$", text):
        return int(text)

    # Also handle Eastern Arabic numerals (۰-۹)
    eastern = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if re.match(r"^\d+$", eastern):
        return int(eastern)

    # Try English
    result = _parse_english(text)
    if result is not None:
        return result

    # Try Urdu (native script)
    result = _parse_map(text, _UR_ONES, _UR_TENS)
    if result is not None:
        return result

    # Try Roman Urdu
    result = _parse_map(text, _RU_ONES, _RU_TENS)
    if result is not None:
        return result

    return None


def _parse_english(text: str) -> int | None:
    """Parse an English number word or phrase."""
    tokens = text.split()
    total = 0
    for token in tokens:
        if token in _EN_ONES:
            total += _EN_ONES[token]
        elif token in _EN_TENS:
            total += _EN_TENS[token]
        else:
            return None
    return total if total > 0 or text in _EN_ONES else None


def _parse_map(text: str, ones: dict, tens: dict) -> int | None:
    """Generic parser using provided ones/tens maps."""
    if text in ones:
        return ones[text]
    if text in tens:
        return tens[text]
    # Try two-token "tens ones" combinations
    for t_word, t_val in tens.items():
        for o_word, o_val in ones.items():
            if text in (f"{t_word} {o_word}", f"{t_word}{o_word}"):
                return t_val + o_val
    return None
