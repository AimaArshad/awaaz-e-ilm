import asyncio
import sounddevice as sd
from app.services.stt import transcribe

def test_stt_live_microphone():
    print("\n🎤 Recording 3 seconds... Speak now! (Say 'play topic on photosynthesis')")
    
    # Record 3 seconds of audio at 16kHz
    samples = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype="int16")
    sd.wait()
    print("✅ Recording finished. Transcribing (this may take a few seconds the first time)...")

    pcm_bytes = samples.tobytes()
    
    # Run the async transcribe function
    result = asyncio.run(transcribe(pcm_bytes, lang=None))
    
    print(f"\n🗣️ Whisper heard: '{result['text']}'")
    print(f"🌍 Detected Language: {result['language']}")
    
    assert len(result['text']) > 0, "Whisper didn't hear anything!"