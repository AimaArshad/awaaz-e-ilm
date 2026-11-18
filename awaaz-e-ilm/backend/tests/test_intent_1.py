# from app.services.intent.parser import parse_intent

# def test_navigate_topic_intents():
#     cases = [
#         ("play the topic on photosynthesis", "photosynthesis"),
#         ("go to the topic about Newton's second law", "Newton's second law"),
#         ("find the section on cell division", "cell division"),
#         ("open the topic on the water cycle", "the water cycle"),
#         ("موضوع سیل ڈویژن", "سیل ڈویژن"), # Urdu test
#     ]
    
#     for text, expected_topic in cases:
#         result = parse_intent(text)
#         print(f"\nInput: '{text}'")
#         print(f"Intent: {result['intent']} | Topic Extracted: {result['params'].get('topic')}")
        
#         assert result["intent"] == "navigate_topic", f"Failed on: {text}"
#         assert result["params"]["topic"].lower() == expected_topic.lower()     
        
        
        
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
    # ("go to chapter five", "navigate_chapter", {"chapter": 5}),
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