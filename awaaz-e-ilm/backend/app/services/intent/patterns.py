"""Intent pattern definitions for voice command parsing.

Each intent maps to one or more regex patterns in English and Urdu.
Patterns are ordered from most specific to least specific.

Intent taxonomy
---------------
navigate_chapter   – go to / open a specific chapter by number
seek_forward       – skip forward by N seconds
seek_backward      – skip backward by N seconds
play               – resume / start playback
pause              – pause playback
set_speed          – change playback speed
set_language       – switch audio language (English / Urdu)
repeat             – replay current sentence / section
help               – show help / list commands
unknown            – unrecognised input
"""
from __future__ import annotations
import re
from typing import Dict, List, Pattern

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------
# Each entry: intent_name → list of compiled regex patterns
# Patterns should use named groups for parameter extraction.
# ---------------------------------------------------------------------------

INTENT_PATTERNS: Dict[str, List[Pattern]] = {
    # "navigate_chapter": [
    #     re.compile(
    #         r"(?:go\s+to|open|jump\s+to)\s+chapter\s+(?P<chapter>\w+)",
    #         re.IGNORECASE,
    #     ),
    #     re.compile(
    #         r"chapter\s+(?P<chapter>\w+)",
    #         re.IGNORECASE,
    #     ),
    #     re.compile(
    #         r"باب\s+(?P<chapter>[\w\u0660-\u0669]+)",  # Urdu "باب N"
    #         re.UNICODE,
    #     ),
    # ],
    # "seek_forward": [
    #     re.compile(
    #         r"(?:skip|forward|fast\s*forward|آگے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
    #         re.IGNORECASE | re.UNICODE,
    #     ),
    #     re.compile(r"آگے\s+(?P<seconds>[\w\u0660-\u0669]+)\s*سیکنڈ", re.UNICODE),
    # ],
    # "seek_backward": [
    #     re.compile(
    #         r"(?:back(?:ward)?|rewind|پیچھے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
    #         re.IGNORECASE | re.UNICODE,
    #     ),
    #     re.compile(r"پیچھے\s+(?P<seconds>[\w\u0660-\u0669]+)\s*سیکنڈ", re.UNICODE),
    # ],




    "navigate_chapter": [
        re.compile(
            r"\b(?:go\s+to|open|jump\s+to)\s+chapter\s+(?P<chapter>\w+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*chapter\s+(?P<chapter>\w+)\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*باب\s+(?P<chapter>[\w\u0660-\u0669]+)",
            re.UNICODE,
        ),
    ],
    "seek_forward": [
        re.compile(
            r"\b(?:skip|forward|fast\s*forward|آگے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
            re.IGNORECASE | re.UNICODE,
        ),
    ],
    "seek_backward": [
        re.compile(
            r"\b(?:back(?:ward)?|rewind|پیچھے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
            re.IGNORECASE | re.UNICODE,
        ),
    ],
    "play": [
        re.compile(r"\b(?:play|resume|start|چلاؤ|شروع)\b", re.IGNORECASE | re.UNICODE),
    ],
    "pause": [
        re.compile(r"\b(?:pause|stop|رکو|بند)\b", re.IGNORECASE | re.UNICODE),
    ],
    "set_speed": [
        re.compile(
            r"(?:set\s+speed|speed)\s+(?:to\s+)?(?P<speed>[\d.]+)(?:x)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:faster|slower|normal\s+speed)",
            re.IGNORECASE,
        ),
    ],
    "set_language": [
        re.compile(
            r"(?:read\s+in|switch\s+to|translate\s+to)\s+(?P<lang>english|urdu|اردو|انگریزی)",
            re.IGNORECASE | re.UNICODE,
        ),
        re.compile(r"اردو\s+میں\s+(?:پڑھو|سناؤ)", re.UNICODE),
    ],
    "repeat": [
        re.compile(r"\b(?:repeat|again|دوبارہ)\b", re.IGNORECASE | re.UNICODE),
    ],
    # "help": [
    #     re.compile(r"\b(?:help|commands?|مدد|کمانڈ)\b", re.IGNORECASE | re.UNICODE),
    # ],


    "help": [
    re.compile(
        r"^\s*(?:help|help me|what can i say|what can you do|(?:list|show|tell me)(?: the)? commands?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(?:مدد|ہیلپ|کمانڈ(?:ز)?)\s*$", re.UNICODE),
],
}
