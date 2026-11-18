import pytest
from types import SimpleNamespace as NS
from app.services.intent.parser import parse_intent
from app.services.library_resolver import canon_tokens, score_title, pick_chapter


@pytest.mark.parametrize("phrase,chapter,book", [
    ("Open chapter 1, physics 2nd year.", 1, "physics 2nd year"),
    ("open chapter five physics first year", 5, "physics first year"),
    ("Go to chapter five.", 5, None),
    ("chapter 12", 12, None),
    ("open chapter twenty five of chemistry", 25, "chemistry"),
    ("open physics first year chapter 3", 3, "physics first year"),
    ("play chapter 2 from the biology book", 2, "biology"),
    ("open chapter for physics", 4, "physics"),            # Whisper: "four" -> "for"
])
def test_open_chapter(phrase, chapter, book):
    r = parse_intent(phrase)
    assert r["intent"] == "open_chapter"
    assert r["params"].get("chapter") == chapter
    assert r["params"].get("book") == book


@pytest.mark.parametrize("phrase,intent,params", [
    ("forward", "seek_forward", {"seconds": 30}),
    ("skip forward thirty seconds", "seek_forward", {"seconds": 30}),
    ("skip 45", "seek_forward", {"seconds": 45}),
    ("go back 10 seconds", "seek_backward", {"seconds": 10}),
    ("rewind", "seek_backward", {"seconds": 30}),
    ("next chapter", "next_chapter", {}),
    ("previous chapter", "prev_chapter", {}),
    ("faster", "set_speed", {"relative": 1.25}),
    ("slow down", "set_speed", {"relative": 0.8}),
    ("speed 1.5", "set_speed", {"speed": 1.5}),
    ("normal speed", "set_speed", {"speed": 1.0}),
    ("read in Urdu", "set_language", {"lang": "ur"}),
    ("play it again", "repeat", {}),
    ("pause", "pause", {}),
    ("resume", "play", {}),
])
def test_controls(phrase, intent, params):
    r = parse_intent(phrase)
    assert r["intent"] == intent and r["params"] == params


def test_topic_still_wins():
    assert parse_intent("play the topic on forward motion")["intent"] == "navigate_topic"


def test_year_aliases():
    q = canon_tokens("physics first year")
    assert score_title(q, canon_tokens("Physics_1st_Year.pdf")) > 0.9
    assert score_title(q, canon_tokens("Physics 11th class")) > 0.9
    assert score_title(q, canon_tokens("Physics 2nd Year")) < 0.6
    assert score_title(q, canon_tokens("Chemistry 1st Year")) < 0.6


def test_pick_chapter_by_title_number():
    chs = [NS(index=0, title="Chapter 12: Waves"), NS(index=1, title="Chapter 13: Thermal Physics")]
    assert pick_chapter(chs, 13).index == 1
    assert pick_chapter(chs, 1) is None


def test_pick_chapter_by_position():
    chs = [NS(index=0, title="Intro"), NS(index=1, title="Heat"), NS(index=2, title="Waves")]
    assert pick_chapter(chs, 2).title == "Heat"
    assert pick_chapter(chs, 9) is None