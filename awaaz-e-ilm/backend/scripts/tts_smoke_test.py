#!/usr/bin/env python
"""TTS smoke test.

Synthesises a short English sentence with Piper and writes the result to
``backend/storage/smoke_en.mp3``.  Prints the real-time factor (seconds of
audio generated per second of CPU time).

Usage:
    cd backend
    python scripts/tts_smoke_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure the backend package is importable
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


def main():
    from app.services.tts.base import get_engine
    import app.services.tts  # noqa: F401  — registers engines

    text = "Hello. This is a test of the English voice."
    print(f"Text: {text!r}")
    print()

    engine = get_engine("en")
    print(f"Engine: {engine.name} (version: {engine.ENGINE_VERSION})")

    # Synthesise and time it
    t0 = time.perf_counter()
    segment = engine.synthesize(text, lang="en")
    wall_time = time.perf_counter() - t0

    audio_duration = len(segment) / 1000.0
    rtf = audio_duration / wall_time if wall_time > 0 else float("inf")

    # Export
    output_dir = backend_dir / "storage"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "smoke_en.mp3"
    segment.export(str(output_path), format="mp3")

    print(f"Audio duration:  {audio_duration:.2f}s")
    print(f"Wall-clock time: {wall_time:.2f}s")
    print(f"Real-time factor: {rtf:.2f}x  ({audio_duration:.2f}s audio / {wall_time:.2f}s CPU)")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()

