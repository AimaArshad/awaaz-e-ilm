from app.services.topic_navigator import find_topic_in_timing

def test_topic_matching():
    # Mock data that looks exactly like your timing.json
    timing = [
        {"idx": 0, "start_s": 0.0,  "end_s": 3.0,  "text": "Welcome to chapter five."},
        {"idx": 1, "start_s": 3.0,  "end_s": 8.0,  "text": "Today we discuss photosynthesis."},
        {"idx": 2, "start_s": 8.0,  "end_s": 14.0, "text": "The process begins in the chloroplast."},
        {"idx": 3, "start_s": 14.0, "end_s": 20.0, "text": "Chlorophyll absorbs light energy."},
    ]

    # 1. Exact match test
    hit1 = find_topic_in_timing(timing, "photosynthesis")
    print(f"\nSearch: 'photosynthesis' -> Found: {hit1['text'] if hit1 else 'None'}")
    assert hit1 is not None
    assert hit1["start_s"] == 3.0

    # 2. Messy voice command test (fuzzy match)
    hit2 = find_topic_in_timing(timing, "the topic on photosynthesis")
    print(f"Search: 'the topic on photosynthesis' -> Found: {hit2['text'] if hit2 else 'None'}")
    assert hit2 is not None
    assert hit2["start_s"] == 3.0

    # 3. Miss test
    hit3 = find_topic_in_timing(timing, "quantum mechanics")
    print(f"Search: 'quantum mechanics' -> Found: {hit3['text'] if hit3 else 'None'}")
    assert hit3 is None