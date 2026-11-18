# """Tests for the voice command intent parser.

# Covers all 9 intents across English, Urdu, and Roman Urdu inputs.
# """
# import pytest

# from app.services.intent.parser import parse_intent
# from app.services.intent.numbers_en_ur import word_to_number


# # ---------------------------------------------------------------------------
# # word_to_number tests
# # ---------------------------------------------------------------------------

# class TestWordToNumber:
#     def test_digit_string(self):
#         assert word_to_number("42") == 42

#     def test_english_simple(self):
#         assert word_to_number("five") == 5

#     def test_english_tens(self):
#         assert word_to_number("thirty") == 30

#     def test_english_compound(self):
#         assert word_to_number("forty two") == 42

#     def test_urdu_simple(self):
#         assert word_to_number("پانچ") == 5

#     def test_urdu_tens(self):
#         assert word_to_number("تیس") == 30

#     def test_roman_urdu_simple(self):
#         assert word_to_number("paanch") == 5

#     def test_roman_urdu_tens(self):
#         assert word_to_number("tees") == 30

#     def test_unknown_returns_none(self):
#         assert word_to_number("blah") is None

#     def test_eastern_arabic_numerals(self):
#         assert word_to_number("۵") == 5


# # ---------------------------------------------------------------------------
# # parse_intent tests
# # ---------------------------------------------------------------------------

# class TestParseIntent:
#     def test_navigate_chapter_english(self):
#         result = parse_intent("go to chapter five")
#         assert result["intent"] == "navigate_chapter"
#         assert result["params"].get("chapter") == 5

#     def test_navigate_chapter_urdu(self):
#         result = parse_intent("باب پانچ")
#         assert result["intent"] == "navigate_chapter"

#     def test_seek_forward_english(self):
#         result = parse_intent("forward thirty seconds")
#         assert result["intent"] == "seek_forward"
#         assert result["params"].get("seconds") == 30

#     def test_seek_backward_english(self):
#         result = parse_intent("back ten seconds")
#         assert result["intent"] == "seek_backward"
#         assert result["params"].get("seconds") == 10

#     def test_play_intent(self):
#         result = parse_intent("play")
#         assert result["intent"] == "play"

#     def test_pause_intent(self):
#         result = parse_intent("pause")
#         assert result["intent"] == "pause"

#     def test_pause_urdu(self):
#         result = parse_intent("رکو")
#         assert result["intent"] == "pause"

#     def test_set_language_urdu(self):
#         result = parse_intent("read in urdu")
#         assert result["intent"] == "set_language"
#         assert result["params"].get("lang") == "ur"

#     def test_set_language_english(self):
#         result = parse_intent("switch to english")
#         assert result["intent"] == "set_language"
#         assert result["params"].get("lang") == "en"

#     def test_help_intent(self):
#         result = parse_intent("help")
#         assert result["intent"] == "help"

#     def test_unknown_intent(self):
#         result = parse_intent("xyz unrecognised command 123")
#         assert result["intent"] == "unknown"
#         assert result["confidence"] == 0.0

#     def test_result_has_raw_field(self):
#         text = "play"
#         result = parse_intent(text)
#         assert result["raw"] == text



import pytest
from app.services.intent.parser import parse_intent


@pytest.mark.parametrize("phrase,topic", [
    ("Play the topic on photosynthesis.", "photosynthesis"),
    ("go to the topic about Newton's second law", "newtons second law"),
    ("find section on kinetic energy please", "kinetic energy"),
    ("Play the topic on forward motion", "forward motion"),   # contains 'forward'
    ("open the section on stopping distance", "stopping distance"),
    ("topic on friction", "friction"),
])
def test_topic(phrase, topic):
    r = parse_intent(phrase)
    assert r["intent"] == "navigate_topic"
    assert r["params"]["topic"] == topic


@pytest.mark.parametrize("phrase,intent,params", [
    ("go to chapter five", "open_chapter", {"chapter": 5}),
    ("forward thirty seconds", "seek_forward", {"seconds": 30}),
    ("rewind 10 seconds", "seek_backward", {"seconds": 10}),
    ("play", "play", {}),
    ("pause", "pause", {}),
    ("help", "help", {}),
])
def test_other_intents(phrase, intent, params):
    r = parse_intent(phrase)
    assert r["intent"] == intent and r["params"] == params