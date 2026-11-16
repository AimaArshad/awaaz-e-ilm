"""Voice command intent parser.

Matches a transcribed utterance against the INTENT_PATTERNS registry and
extracts structured parameters (chapter number, seek seconds, speed, etc.).

Returns a dict:
    {
        "intent": str,          # e.g. "navigate_chapter"
        "params": dict,         # e.g. {"chapter": 5}
        "confidence": float,    # 1.0 for rule-based, 0.0 for unknown
        "raw": str,             # original transcript (unchanged)
    }
"""
from __future__ import annotations

import re

from app.services.intent.numbers_en_ur import word_to_number
from app.services.intent.patterns import INTENT_PATTERNS

# Language name aliases used in set_language intent
_LANG_MAP = {
    "english": "en",
    "urdu": "ur",
    "اردو": "ur",
    "انگریزی": "en",
}

# Speed aliases used in set_speed intent
_SPEED_ALIASES = {
    "faster": 1.5,
    "slower": 0.75,
    "normal speed": 1.0,
    "normal": 1.0,
}

# Intents that are only valid if a number was successfully extracted.
_REQUIRED_PARAM = {
    "navigate_chapter": "chapter",
    "seek_forward": "seconds",
    "seek_backward": "seconds",
}


def _normalize(text: str) -> str:
    """Normalize text for matching only (the original is kept as `raw`).

    Lowercases, strips English and Urdu punctuation, and collapses spaces.
    Decimal points inside numbers (e.g. "speed 1.5") are preserved.
    """
    text = text.strip().lower()
    # Punctuation that never matters for commands (English + Urdu marks)
    text = re.sub(r"[,!?؟۔،;:\"'()\[\]]+", " ", text)
    # Dots that are not between two digits
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_intent(text: str) -> dict:
    """Parse a transcribed voice command into a structured intent dict.

    Args:
        text: Transcribed speech (may be English, Urdu, or Roman Urdu).

    Returns:
        Dict with keys: intent, params, confidence, raw.

    Examples:
        >>> parse_intent("go to chapter five")
        {"intent": "navigate_chapter", "params": {"chapter": 5}, "confidence": 1.0, "raw": "go to chapter five"}

        >>> parse_intent("forward thirty seconds")
        {"intent": "seek_forward", "params": {"seconds": 30}, "confidence": 1.0, "raw": "forward thirty seconds"}
    """
    raw = text
    normalized = _normalize(text)

    if not normalized:
        return {"intent": "unknown", "params": {}, "confidence": 0.0, "raw": raw}

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            m = pattern.search(normalized)
            if not m:
                continue

            params = _extract_params(intent, m)

            # If a number is required but could not be parsed (e.g. "forward
            # the file"), this is not a real command: try the next pattern.
            required = _REQUIRED_PARAM.get(intent)
            if required and required not in params:
                continue

            return {
                "intent": intent,
                "params": params,
                "confidence": 1.0,
                "raw": raw,
            }

    return {"intent": "unknown", "params": {}, "confidence": 0.0, "raw": raw}


# ---------------------------------------------------------------------------
# Parameter extraction helpers
# ---------------------------------------------------------------------------

def _extract_params(intent: str, match) -> dict:
    """Extract and coerce named groups from a regex match."""
    groups = match.groupdict()
    params: dict = {}

    if intent == "navigate_chapter":
        chapter_word = groups.get("chapter", "") or ""
        chapter_num = word_to_number(chapter_word)
        if chapter_num is not None:
            params["chapter"] = chapter_num

    elif intent in ("seek_forward", "seek_backward"):
        seconds_word = groups.get("seconds", "") or ""
        seconds = word_to_number(seconds_word)
        if seconds is not None:
            params["seconds"] = seconds

    elif intent == "set_speed":
        speed_str = groups.get("speed", "") or ""
        # Handle aliases like "faster", "slower"
        matched_text = match.group(0).lower()
        for alias, val in _SPEED_ALIASES.items():
            if alias in matched_text:
                params["speed"] = val
                break
        else:
            try:
                params["speed"] = float(speed_str)
            except (ValueError, TypeError):
                pass

    elif intent == "set_language":
        lang_word = (groups.get("lang") or "").lower()
        params["lang"] = _LANG_MAP.get(lang_word, lang_word)

    return params