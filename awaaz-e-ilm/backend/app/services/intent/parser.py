# """Voice command intent parser.

# Matches a transcribed utterance against the INTENT_PATTERNS registry and
# extracts structured parameters (chapter number, seek seconds, speed, etc.).

# Returns a dict:
#     {
#         "intent": str,          # e.g. "navigate_chapter"
#         "params": dict,         # e.g. {"chapter": 5}
#         "confidence": float,    # 1.0 for rule-based, 0.0 for unknown
#         "raw": str,             # original transcript (unchanged)
#     }
# """
# from __future__ import annotations

# import re

# from app.services.intent.numbers_en_ur import word_to_number
# from app.services.intent.patterns import INTENT_PATTERNS

# # Language name aliases used in set_language intent
# _LANG_MAP = {
#     "english": "en",
#     "urdu": "ur",
#     "اردو": "ur",
#     "انگریزی": "en",
# }

# # Speed aliases used in set_speed intent
# _SPEED_ALIASES = {
#     "faster": 1.5,
#     "slower": 0.75,
#     "normal speed": 1.0,
#     "normal": 1.0,
# }

# # Intents that are only valid if a number was successfully extracted.
# _REQUIRED_PARAM = {
#     "navigate_chapter": "chapter",
#     "seek_forward": "seconds",
#     "seek_backward": "seconds",
#      "navigate_topic": "topic",
# }


# # def _normalize(text: str) -> str:
# #     """Normalize text for matching only (the original is kept as `raw`).

# #     Lowercases, strips English and Urdu punctuation, and collapses spaces.
# #     Decimal points inside numbers (e.g. "speed 1.5") are preserved.
# #     """
# #     text = text.strip().lower()
# #     # Punctuation that never matters for commands (English + Urdu marks)
# #     text = re.sub(r"[,!?؟۔،;:\"'()\[\]]+", " ", text)
# #     # Dots that are not between two digits
# #     text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)
# #     return re.sub(r"\s+", " ", text).strip()


# def _normalize(text: str) -> str:
#     text = text.strip().lower()
#     text = re.sub(r"['’]", "", text)                       # newton's -> newtons
#     text = re.sub(r"[,!?؟۔،;:\"()\[\]]+", " ", text)
#     text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)        # keep "1.5"
#     return re.sub(r"\s+", " ", text).strip()

# def parse_intent(text: str) -> dict:
#     """Parse a transcribed voice command into a structured intent dict.

#     Args:
#         text: Transcribed speech (may be English, Urdu, or Roman Urdu).

#     Returns:
#         Dict with keys: intent, params, confidence, raw.

#     Examples:
#         >>> parse_intent("go to chapter five")
#         {"intent": "navigate_chapter", "params": {"chapter": 5}, "confidence": 1.0, "raw": "go to chapter five"}

#         >>> parse_intent("forward thirty seconds")
#         {"intent": "seek_forward", "params": {"seconds": 30}, "confidence": 1.0, "raw": "forward thirty seconds"}
#     """
#     raw = text
#     normalized = _normalize(text)

#     if not normalized:
#         return {"intent": "unknown", "params": {}, "confidence": 0.0, "raw": raw}

#     for intent, patterns in INTENT_PATTERNS.items():
#         for pattern in patterns:
#             m = pattern.search(normalized)
#             if not m:
#                 continue

#             params = _extract_params(intent, m)

#             # If a number is required but could not be parsed (e.g. "forward
#             # the file"), this is not a real command: try the next pattern.
#             required = _REQUIRED_PARAM.get(intent)
#             if required and required not in params:
#                 continue

#             return {
#                 "intent": intent,
#                 "params": params,
#                 "confidence": 1.0,
#                 "raw": raw,
#             }

#     return {"intent": "unknown", "params": {}, "confidence": 0.0, "raw": raw}


# # ---------------------------------------------------------------------------
# # Parameter extraction helpers
# # ---------------------------------------------------------------------------

# def _extract_params(intent: str, match) -> dict:
#     """Extract and coerce named groups from a regex match."""
#     groups = match.groupdict()
#     params: dict = {}

#     if intent == "navigate_chapter":
#         chapter_word = groups.get("chapter", "") or ""
#         chapter_num = word_to_number(chapter_word)
#         if chapter_num is not None:
#             params["chapter"] = chapter_num

#     elif intent in ("seek_forward", "seek_backward"):
#         seconds_word = groups.get("seconds", "") or ""
#         seconds = word_to_number(seconds_word)
#         if seconds is not None:
#             params["seconds"] = seconds

#     elif intent == "set_speed":
#         speed_str = groups.get("speed", "") or ""
#         # Handle aliases like "faster", "slower"
#         matched_text = match.group(0).lower()
#         for alias, val in _SPEED_ALIASES.items():
#             if alias in matched_text:
#                 params["speed"] = val
#                 break
#         else:
#             try:
#                 params["speed"] = float(speed_str)
#             except (ValueError, TypeError):
#                 pass

#     elif intent == "set_language":
#         lang_word = (groups.get("lang") or "").lower()
#         params["lang"] = _LANG_MAP.get(lang_word, lang_word)
        
        
#     # elif intent == "navigate_topic":
#     #     topic = (groups.get("topic") or "").strip()
#     #     # Trim trailing punctuation Whisper sometimes adds
#     #     topic = topic.rstrip(".,!?؟۔")
#     #     if topic:
#     #         params["topic"] = topic    
            
            
#     elif intent == "navigate_topic":
#         topic = (groups.get("topic") or "").strip()
#         topic = re.sub(r"(?:\s+(?:please|now|thanks|thank you|for me))+$", "", topic).strip()
#         if topic:
#             params["topic"] = topic         

#     return params


"""Voice command intent parser.

Returns {"intent", "params", "confidence", "raw"}.
"""
from __future__ import annotations

import re

from app.services.intent.numbers_en_ur import word_to_number
from app.services.intent.patterns import INTENT_PATTERNS

_LANG_MAP = {"english": "en", "urdu": "ur", "اردو": "ur", "انگریزی": "en"}

# (phrase, params). First phrase found in the matched text wins.
_SPEED_ALIASES = [
    ("normal speed", {"speed": 1.0}),
    ("faster", {"relative": 1.25}),
    ("speed up", {"relative": 1.25}),
    ("slower", {"relative": 0.8}),
    ("slow down", {"relative": 0.8}),
]

_REQUIRED_PARAM = {
    "open_chapter": "chapter",
    "seek_forward": "seconds",
    "seek_backward": "seconds",
    "navigate_topic": "topic",
}

_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}
# Whisper often writes number words as their homophones in short commands.
_HOMOPHONES = {"to": 2, "too": 2, "for": 4, "fore": 4, "won": 1, "ate": 8}

_BOOK_FILLER = re.compile(
    r"^(?:(?:of|from|in|the|book|for|on|at)\s+)+"
    r"|(?:\s+(?:please|now|book|thanks|thank\s+you))+$"
)


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[,!?؟۔،;:\"()\[\]]+", " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)  # keep "1.5"
    return re.sub(r"\s+", " ", text).strip()


def parse_intent(text: str) -> dict:
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
            required = _REQUIRED_PARAM.get(intent)
            if required and required not in params:
                continue  # not a real command: try the next pattern
            return {"intent": intent, "params": params, "confidence": 1.0, "raw": raw}

    return {"intent": "unknown", "params": {}, "confidence": 0.0, "raw": raw}


# ---------------------------------------------------------------------------

def _chapter_number(text: str) -> int | None:
    t = text.strip().lower()
    if t in _HOMOPHONES:
        return _HOMOPHONES[t]
    if t in _ORDINALS:
        return _ORDINALS[t]
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th)", t)
    if m:
        return int(m.group(1))
    n = word_to_number(t)
    return n if n is not None and n >= 1 else None


def _clean_book(text: str) -> str:
    text = text.strip()
    for _ in range(2):
        text = _BOOK_FILLER.sub("", text).strip()
    return text


def _extract_open_chapter(groups: dict) -> dict:
    tokens = (groups.get("rest") or "").split()
    book_before = (groups.get("book") or "").strip()
    params: dict = {}
    for n in (2, 1):                      # "twenty five" first, then "five"
        if len(tokens) >= n:
            num = _chapter_number(" ".join(tokens[:n]))
            if num is not None:
                params["chapter"] = num
                tokens = tokens[n:]
                break
    if "chapter" not in params:
        return {}
    book = _clean_book(" ".join([book_before] + tokens))
    if book:
        params["book"] = book
    return params


def _extract_params(intent: str, match) -> dict:
    groups = match.groupdict()
    params: dict = {}

    if intent == "open_chapter":
        return _extract_open_chapter(groups)

    if intent in ("seek_forward", "seek_backward"):
        raw = groups.get("seconds")
        if raw is None:                       # bare "forward" / "rewind"
            params["seconds"] = 30
        else:
            n = word_to_number(raw)
            if n is not None:
                params["seconds"] = n

    elif intent == "set_speed":
        matched = match.group(0).lower()
        for alias, val in _SPEED_ALIASES:
            if alias in matched:
                params.update(val)
                break
        else:
            try:
                params["speed"] = float(groups.get("speed") or "")
            except ValueError:
                pass

    elif intent == "set_language":
        word = (groups.get("lang") or "").lower()
        params["lang"] = _LANG_MAP.get(word, word) or "ur"   # the Urdu sentence pattern has no group

    elif intent == "navigate_topic":
        topic = (groups.get("topic") or "").strip()
        topic = re.sub(r"(?:\s+(?:please|now|thanks|thank you|for me))+$", "", topic).strip()
        if topic:
            params["topic"] = topic

    return params