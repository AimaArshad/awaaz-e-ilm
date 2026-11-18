# import asyncio
# import json
# import sounddevice as sd
# import websockets
# import pytest

# @pytest.mark.asyncio
# async def test_voice_websocket_full_flow():
#     # NOTE: You must have the server running in another terminal for this to work!
#     uri = "ws://localhost:8000/ws/voice"
    
#     try:
#         async with websockets.connect(uri) as ws:
#             # 1. Tell the backend which chapter is playing
#             # Change '1' to a real chapter ID from your database that has a timing.json!
#             await ws.send(json.dumps({"action": "set_chapter", "chapter_id": 1}))
            
#             print("\n🎤 Recording 4 seconds... Speak now! (Say 'play the topic on <something in chapter 1>')")
#             samples = sd.rec(int(4 * 16000), samplerate=16000, channels=1, dtype="int16")
#             sd.wait()
#             print("✅ Sending audio to server...")

#             # 2. Send audio and tell server we stopped speaking
#             await ws.send(samples.tobytes())
#             await ws.send(json.dumps({"action": "end_speech"}))

#             # 3. Wait for the server's response
#             response = await ws.recv()
#             data = json.loads(response)
            
#             print(f"\n📥 Server Response: {json.dumps(data, indent=2)}")
            
#             # 4. Check the results
#             assert data["action"] in ["seek_and_play", "not_found", "error"], "Unexpected action"
            
#             if data["action"] == "seek_and_play":
#                 print("🎉 SUCCESS! The server found the topic and told the frontend to seek.")
#             else:
#                 print(f"⚠️ Server responded with: {data.get('message')}")
                
#     except ConnectionRefusedError:
#         pytest.fail("Server is not running! Start it with 'uvicorn app.main:app --reload' first.")




"""Usage (from backend/, server running):
python scripts/voice_probe.py --chapter 1 --phrase "play the topic on photosynthesis"
"""
import argparse, asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import websockets
from pydub import AudioSegment


async def main(a):
    from app.services.tts.base import get_engine
    import app.services.tts  # noqa: F401 (registers engines)

    seg = (AudioSegment.silent(300)
           + get_engine("en").synthesize(a.phrase, lang="en")
           + AudioSegment.silent(300))
    pcm = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2).raw_data

    async with websockets.connect(a.url) as ws:
        await ws.send(json.dumps({"action": "set_chapter", "chapter_id": a.chapter}))
        for i in range(0, len(pcm), 8192):
            await ws.send(pcm[i:i + 8192])
        await ws.send(json.dumps({"action": "end_speech"}))

        loop = asyncio.get_event_loop()
        deadline = loop.time() + a.wait
        while (left := deadline - loop.time()) > 0:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=left))
            except asyncio.TimeoutError:
                break
            print(msg)
            if msg["action"] != "generating":  # keep waiting only for generation_complete
                break


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--chapter", type=int, required=True)
    p.add_argument("--phrase", required=True)
    p.add_argument("--url", default="ws://localhost:8000/ws/voice")
    p.add_argument("--wait", type=int, default=900)
    asyncio.run(main(p.parse_args()))