# """Usage: python scripts/topic_probe.py <timing.json> "<topic>" """
# import json, sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# from app.services.topic_navigator import find_topic_in_timing

# timing = json.load(open(sys.argv[1], encoding="utf-8"))
# hit = find_topic_in_timing(timing, sys.argv[2])
# print(hit if hit else "NO MATCH")


# # if __name__ == "__main__":
# #     p = argparse.ArgumentParser()
# #     p.add_argument("--chapter", type=int, required=True)
# #     p.add_argument("--phrase", required=True)
# #     p.add_argument("--url", default="ws://localhost:8000/ws/voice")
# #     p.add_argument("--wait", type=int, default=900)
# #     asyncio.run(main(p.parse_args()))


"""Usage (from backend/): python scripts/topic_probe.py <timing.json> "<topic>" """
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.topic_navigator import find_topic_in_timing


def main() -> None:
    if len(sys.argv) < 3:
        print('Usage: python scripts/topic_probe.py <timing.json> "<topic>"')
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        timing = json.load(f)
    hit = find_topic_in_timing(timing, sys.argv[2])
    print(hit if hit else "NO MATCH")


if __name__ == "__main__":
    main()