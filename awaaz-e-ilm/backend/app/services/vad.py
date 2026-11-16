"""Voice Activity Detection (VAD) service.

Milestone 4 implementation plan
--------------------------------
Uses Silero VAD (via torchaudio or the ONNX runtime version) to detect
speech segments in an audio stream.

Purpose
-------
The WebSocket voice endpoint accumulates audio chunks from the client.
VAD determines when the user has finished speaking so we can submit the
audio segment to Whisper for transcription without long silence tails.

Usage pattern
-------------
    vad = VADStream(sample_rate=16000)
    for chunk in audio_stream:
        vad.feed(chunk)
        if vad.end_of_speech():
            audio = vad.flush()
            transcript = await stt.transcribe(audio)
"""
from __future__ import annotations


class VADStream:
    """Stateful VAD accumulator for streaming audio.

    TODO (Milestone 4):
        - Load Silero VAD model (ONNX or torch).
        - Implement `feed(chunk)`, `end_of_speech()`, `flush()`.
    """

    def __init__(self, sample_rate: int = 16_000):
        self.sample_rate = sample_rate
        self._buffer: list[bytes] = []

    def feed(self, chunk: bytes) -> None:
        """Add a raw PCM audio chunk to the buffer."""
        self._buffer.append(chunk)

    def end_of_speech(self) -> bool:
        """Return True when VAD detects end of speech.

        TODO (Milestone 4): Replace with Silero VAD inference.
        """
        # Stub: treat every 3 seconds of audio (3 * 16000 * 2 bytes) as end-of-speech
        total = sum(len(c) for c in self._buffer)
        return total >= 3 * self.sample_rate * 2

    def flush(self) -> bytes:
        """Return accumulated audio and reset buffer."""
        audio = b"".join(self._buffer)
        self._buffer.clear()
        return audio
