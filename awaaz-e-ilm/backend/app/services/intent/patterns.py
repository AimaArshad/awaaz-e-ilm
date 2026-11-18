# # """Intent pattern definitions for voice command parsing.

# # Each intent maps to one or more regex patterns in English and Urdu.
# # Patterns are ordered from most specific to least specific.

# # Intent taxonomy
# # ---------------
# # navigate_chapter   – go to / open a specific chapter by number
# # seek_forward       – skip forward by N seconds
# # seek_backward      – skip backward by N seconds
# # play               – resume / start playback
# # pause              – pause playback
# # set_speed          – change playback speed
# # set_language       – switch audio language (English / Urdu)
# # repeat             – replay current sentence / section
# # help               – show help / list commands
# # unknown            – unrecognised input
# # """
# # from __future__ import annotations
# # import re
# # from typing import Dict, List, Pattern

# # # ---------------------------------------------------------------------------
# # # Pattern registry
# # # ---------------------------------------------------------------------------
# # # Each entry: intent_name → list of compiled regex patterns
# # # Patterns should use named groups for parameter extraction.
# # # ---------------------------------------------------------------------------

# # INTENT_PATTERNS: Dict[str, List[Pattern]] = {
# #     # "navigate_chapter": [
# #     #     re.compile(
# #     #         r"(?:go\s+to|open|jump\s+to)\s+chapter\s+(?P<chapter>\w+)",
# #     #         re.IGNORECASE,
# #     #     ),
# #     #     re.compile(
# #     #         r"chapter\s+(?P<chapter>\w+)",
# #     #         re.IGNORECASE,
# #     #     ),
# #     #     re.compile(
# #     #         r"باب\s+(?P<chapter>[\w\u0660-\u0669]+)",  # Urdu "باب N"
# #     #         re.UNICODE,
# #     #     ),
# #     # ],
# #     # "seek_forward": [
# #     #     re.compile(
# #     #         r"(?:skip|forward|fast\s*forward|آگے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
# #     #         re.IGNORECASE | re.UNICODE,
# #     #     ),
# #     #     re.compile(r"آگے\s+(?P<seconds>[\w\u0660-\u0669]+)\s*سیکنڈ", re.UNICODE),
# #     # ],
# #     # "seek_backward": [
# #     #     re.compile(
# #     #         r"(?:back(?:ward)?|rewind|پیچھے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
# #     #         re.IGNORECASE | re.UNICODE,
# #     #     ),
# #     #     re.compile(r"پیچھے\s+(?P<seconds>[\w\u0660-\u0669]+)\s*سیکنڈ", re.UNICODE),
# #     # ],




# #     "navigate_chapter": [
# #         re.compile(
# #             r"\b(?:go\s+to|open|jump\s+to)\s+chapter\s+(?P<chapter>\w+)",
# #             re.IGNORECASE,
# #         ),
# #         re.compile(
# #             r"^\s*chapter\s+(?P<chapter>\w+)\s*$",
# #             re.IGNORECASE,
# #         ),
# #         re.compile(
# #             r"^\s*باب\s+(?P<chapter>[\w\u0660-\u0669]+)",
# #             re.UNICODE,
# #         ),
# #     ],
# #     "seek_forward": [
# #         re.compile(
# #             r"\b(?:skip|forward|fast\s*forward|آگے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
# #             re.IGNORECASE | re.UNICODE,
# #         ),
# #     ],
# #     "seek_backward": [
# #         re.compile(
# #             r"\b(?:back(?:ward)?|rewind|پیچھے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
# #             re.IGNORECASE | re.UNICODE,
# #         ),
# #     ],
# #     "play": [
# #         re.compile(r"\b(?:play|resume|start|چلاؤ|شروع)\b", re.IGNORECASE | re.UNICODE),
# #     ],
# #     "pause": [
# #         re.compile(r"\b(?:pause|stop|رکو|بند)\b", re.IGNORECASE | re.UNICODE),
# #     ],
# #     "set_speed": [
# #         re.compile(
# #             r"(?:set\s+speed|speed)\s+(?:to\s+)?(?P<speed>[\d.]+)(?:x)?",
# #             re.IGNORECASE,
# #         ),
# #         re.compile(
# #             r"(?:faster|slower|normal\s+speed)",
# #             re.IGNORECASE,
# #         ),
# #     ],
# #     "set_language": [
# #         re.compile(
# #             r"(?:read\s+in|switch\s+to|translate\s+to)\s+(?P<lang>english|urdu|اردو|انگریزی)",
# #             re.IGNORECASE | re.UNICODE,
# #         ),
# #         re.compile(r"اردو\s+میں\s+(?:پڑھو|سناؤ)", re.UNICODE),
# #     ],
# #     "repeat": [
# #         re.compile(r"\b(?:repeat|again|دوبارہ)\b", re.IGNORECASE | re.UNICODE),
# #     ],
# #     # "help": [
# #     #     re.compile(r"\b(?:help|commands?|مدد|کمانڈ)\b", re.IGNORECASE | re.UNICODE),
# #     # ],
# #     "navigate_topic": [
# #         # "play the topic on X", "go to the topic about X", "find section on X"
# #         re.compile(
# #             r"\b(?:play|find|go\s+to|open|jump\s+to)\s+"
# #             r"(?:the\s+)?(?:topic|section|part)\s+"
# #             r"(?:on|about|regarding)\s+(?P<topic>.+)",
# #             re.IGNORECASE,
# #         ),
# #         # "play topic X" (no preposition)
# #         re.compile(
# #             r"\b(?:play|find|go\s+to|open)\s+"
# #             r"(?:the\s+)?(?:topic|section|part)\s+(?P<topic>.+)",
# #             re.IGNORECASE,
# #         ),
# #         # bare "topic on X"
# #         re.compile(
# #             r"\b(?:topic|section|part)\s+(?:on|about)\s+(?P<topic>.+)",
# #             re.IGNORECASE,
# #         ),
# #         # Urdu: "موضوع X پڑھو" or "موضوع X"
# #         re.compile(
# #             r"(?:موضوع|سیکشن)\s+(?:پر\s+)?(?P<topic>.+)",
# #             re.UNICODE,
# #         ),
# #     ],

# #     "help": [
# #     re.compile(
# #         r"^\s*(?:help|help me|what can i say|what can you do|(?:list|show|tell me)(?: the)? commands?)\s*$",
# #         re.IGNORECASE,
# #     ),
# #     re.compile(r"^\s*(?:مدد|ہیلپ|کمانڈ(?:ز)?)\s*$", re.UNICODE),
# # ],
# # }





# """Intent pattern definitions for voice command parsing.

# IMPORTANT: dict order = priority. ``navigate_topic`` must stay FIRST, because
# a topic name can contain words like "play", "stop", "again" or "forward".
# """
# from __future__ import annotations
# import re
# from typing import Dict, List, Pattern

# INTENT_PATTERNS: Dict[str, List[Pattern]] = {
#     # ── Topic navigation (must be first) ──────────────────────────────
#     "navigate_topic": [
#         # "play the topic on X", "go to the section about X", "take me to the part about X"
#         re.compile(
#             r"\b(?:play|find|go\s+to|open|jump\s+to|take\s+me\s+to)\s+"
#             r"(?:the\s+)?(?:topic|section|part)\s+"
#             r"(?:on|about|regarding)\s+(?P<topic>.+)",
#             re.IGNORECASE,
#         ),
#         # "play topic X" (no preposition). "part" is excluded on purpose ("open part two").
#         re.compile(
#             r"\b(?:play|find|go\s+to|open|jump\s+to)\s+"
#             r"(?:the\s+)?(?:topic|section)\s+(?P<topic>.+)",
#             re.IGNORECASE,
#         ),
#         # bare "topic on X"
#         re.compile(
#             r"\b(?:topic|section|part)\s+(?:on|about)\s+(?P<topic>.+)",
#             re.IGNORECASE,
#         ),
#         # Urdu: "موضوع X" / "سیکشن پر X"
#         re.compile(r"(?:موضوع|سیکشن)\s+(?:پر\s+)?(?P<topic>.+)", re.UNICODE),
#     ],
#     "navigate_chapter": [
#         re.compile(r"\b(?:go\s+to|open|jump\s+to)\s+chapter\s+(?P<chapter>\w+)", re.IGNORECASE),
#         re.compile(r"^\s*chapter\s+(?P<chapter>\w+)\s*$", re.IGNORECASE),
#         re.compile(r"^\s*باب\s+(?P<chapter>[\w\u0660-\u0669]+)", re.UNICODE),
#     ],
#     "seek_forward": [
#         re.compile(
#             r"\b(?:skip|forward|fast\s*forward|آگے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
#             re.IGNORECASE | re.UNICODE,
#         ),
#     ],
#     "seek_backward": [
#         re.compile(
#             r"\b(?:back(?:ward)?|rewind|پیچھے)\s+(?P<seconds>\w+)\s*(?:seconds?|s|سیکنڈ)?",
#             re.IGNORECASE | re.UNICODE,
#         ),
#     ],
#     "play": [
#         re.compile(r"\b(?:play|resume|start|چلاؤ|شروع)\b", re.IGNORECASE | re.UNICODE),
#     ],
#     "pause": [
#         re.compile(r"\b(?:pause|stop|رکو|بند)\b", re.IGNORECASE | re.UNICODE),
#     ],
#     "set_speed": [
#         re.compile(r"(?:set\s+speed|speed)\s+(?:to\s+)?(?P<speed>[\d.]+)(?:x)?", re.IGNORECASE),
#         re.compile(r"(?:faster|slower|normal\s+speed)", re.IGNORECASE),
#     ],
#     "set_language": [
#         re.compile(
#             r"(?:read\s+in|switch\s+to|translate\s+to)\s+(?P<lang>english|urdu|اردو|انگریزی)",
#             re.IGNORECASE | re.UNICODE,
#         ),
#         re.compile(r"اردو\s+میں\s+(?:پڑھو|سناؤ)", re.UNICODE),
#     ],
#     "repeat": [
#         re.compile(r"\b(?:repeat|again|دوبارہ)\b", re.IGNORECASE | re.UNICODE),
#     ],
#     "help": [
#         re.compile(
#             r"^\s*(?:help|help me|what can i say|what can you do|"
#             r"(?:list|show|tell me)(?: the)? commands?)\s*$",
#             re.IGNORECASE,
#         ),
#         re.compile(r"^\s*(?:مدد|ہیلپ|کمانڈ(?:ز)?)\s*$", re.UNICODE),
#     ],
# }


"""Intent pattern definitions. Dict order = priority.

navigate_topic must stay first (topic names can contain 'play', 'stop', 'forward'...).
open_chapter / next / prev must come before play/pause.
"""
from __future__ import annotations
import re
from typing import Dict, List, Pattern

_I = re.IGNORECASE
_IU = re.IGNORECASE | re.UNICODE

INTENT_PATTERNS: Dict[str, List[Pattern]] = {
    "navigate_topic": [
        re.compile(
            r"\b(?:play|find|go\s+to|open|jump\s+to|take\s+me\s+to)\s+"
            r"(?:the\s+)?(?:topic|section|part)\s+"
            r"(?:on|about|regarding)\s+(?P<topic>.+)", _I),
        re.compile(
            r"\b(?:play|find|go\s+to|open|jump\s+to)\s+"
            r"(?:the\s+)?(?:topic|section)\s+(?P<topic>.+)", _I),
        re.compile(r"\b(?:topic|section|part)\s+(?:on|about)\s+(?P<topic>.+)", _I),
        re.compile(r"(?:موضوع|سیکشن)\s+(?:پر\s+)?(?P<topic>.+)", re.UNICODE),
    ],
    "next_chapter": [
        re.compile(r"^\s*(?:(?:go|skip|jump|play|open)\s+(?:to\s+)?)?(?:the\s+)?next\s+chapter\s*$", _I),
        re.compile(r"^\s*اگلا\s+باب\s*$", re.UNICODE),
    ],
    "prev_chapter": [
        re.compile(
            r"^\s*(?:(?:go|jump|play|open)\s+(?:back\s+)?(?:to\s+)?)?(?:the\s+)?"
            r"(?:previous|prior)\s+chapter\s*$", _I),
        re.compile(r"^\s*پچھلا\s+باب\s*$", re.UNICODE),
    ],
    "open_chapter": [
        # "open chapter 5 physics first year", "go to chapter five", "chapter 5"
        re.compile(
            r"^\s*(?:please\s+)?(?:(?:open|play|go\s+to|jump\s+to|start|read|load|"
            r"take\s+me\s+to|switch\s+to)\s+)?(?:the\s+)?chapter\s+(?P<rest>.+?)\s*$", _I),
        # "open physics first year chapter 3"
        re.compile(
            r"^\s*(?:please\s+)?(?:open|play|go\s+to|load|start|read)\s+(?:the\s+)?"
            r"(?P<book>.+?)\s+chapter\s+(?P<rest>.+?)\s*$", _I),
        # Urdu: "باب پانچ"
        re.compile(r"^\s*(?:(?:کھولو|چلاؤ)\s+)?باب\s+(?P<rest>.+?)\s*$", re.UNICODE),
    ],
    "seek_forward": [
        re.compile(
            r"\b(?:(?:skip|fast\s*forward|forward|آگے)(?:\s+(?:forward|ahead))?)\s+"
            r"(?P<seconds>\w+)\s*(?:seconds?|secs?|s|سیکنڈ)?", _IU),
        re.compile(r"^\s*(?:skip(?:\s+forward)?|(?:fast\s*)?forward|go\s+forward)\s*$", _I),
    ],
    "seek_backward": [
        re.compile(
            r"\b(?:back(?:ward)?|rewind|go\s+back|پیچھے)\s+"
            r"(?P<seconds>\w+)\s*(?:seconds?|secs?|s|سیکنڈ)?", _IU),
        re.compile(r"^\s*(?:back(?:ward)?|rewind|go\s+back)\s*$", _I),
    ],
    "set_speed": [
        re.compile(r"(?:set\s+speed|speed)\s+(?:to\s+)?(?P<speed>[\d.]+)(?:x)?", _I),
        re.compile(r"(?:faster|slower|speed\s+up|slow\s+down|normal\s+speed)", _I),
    ],
    "set_language": [
        re.compile(
            r"(?:read\s+in|switch\s+to|translate\s+to)\s+(?P<lang>english|urdu|اردو|انگریزی)",
            _IU),
        re.compile(r"اردو\s+میں\s+(?:پڑھو|سناؤ)", re.UNICODE),
    ],
    "repeat": [
        re.compile(r"\b(?:repeat|again|دوبارہ)\b", _IU),
    ],
    "play": [
        re.compile(r"\b(?:play|resume|continue|start|چلاؤ|شروع)\b", _IU),
    ],
    "pause": [
        re.compile(r"\b(?:pause|stop|رکو|بند)\b", _IU),
    ],
    "help": [
        re.compile(
            r"^\s*(?:help|help me|what can i say|what can you do|"
            r"(?:list|show|tell me)(?: the)? commands?)\s*$", _I),
        re.compile(r"^\s*(?:مدد|ہیلپ|کمانڈ(?:ز)?)\s*$", re.UNICODE),
    ],
}