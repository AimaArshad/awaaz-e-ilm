"""Audio stitching service.

Concatenates per-sentence ``AudioSegment`` clips into a single chapter
MP3 file, inserting configurable silence between sentences (300 ms) and
paragraphs (700 ms).  Also produces a sidecar timing JSON so the frontend
can highlight the transcript in sync with playback.

Dependencies: pydub (wraps ffmpeg).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Defaults
SENTENCE_PAUSE_MS = 300
PARAGRAPH_PAUSE_MS = 700


def stitch_and_export(
    paragraphs: List[List[AudioSegment]],
    sentences_text: List[List[str]],
    output_mp3: Path,
    timing_json: Path,
    sentence_pause_ms: int = SENTENCE_PAUSE_MS,
    paragraph_pause_ms: int = PARAGRAPH_PAUSE_MS,
) -> tuple[float, list[dict]]:
    """Stitch sentence audio clips into one MP3 and write timing JSON.

    Args:
        paragraphs: Nested list — paragraphs → sentences of AudioSegments.
        sentences_text: Matching nested list of sentence strings.
        output_mp3: Destination path for the MP3 file.
        timing_json: Destination path for the timing sidecar.
        sentence_pause_ms: Silence inserted between sentences.
        paragraph_pause_ms: Silence inserted between paragraphs.

    Returns:
        Tuple of (total_duration_seconds, timing_entries).
    """
    # Ensure output directories exist
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    timing_json.parent.mkdir(parents=True, exist_ok=True)

    combined = AudioSegment.empty()
    timing: list[dict] = []
    idx = 0
    current_ms = 0.0

    for p_idx, (para_clips, para_texts) in enumerate(zip(paragraphs, sentences_text)):
        for s_idx, (clip, text) in enumerate(zip(para_clips, para_texts)):
            start_s = current_ms / 1000.0
            combined += clip
            current_ms += len(clip)
            end_s = current_ms / 1000.0

            timing.append({
                "idx": idx,
                "start_s": round(start_s, 3),
                "end_s": round(end_s, 3),
                "text": text,
            })
            idx += 1

            # Insert sentence pause (not after the last sentence of the last paragraph)
            is_last_sentence_of_para = (s_idx == len(para_clips) - 1)
            is_last_para = (p_idx == len(paragraphs) - 1)

            if is_last_sentence_of_para and not is_last_para:
                # Paragraph pause
                silence = AudioSegment.silent(duration=paragraph_pause_ms)
                combined += silence
                current_ms += paragraph_pause_ms
            elif not is_last_sentence_of_para:
                # Sentence pause
                silence = AudioSegment.silent(duration=sentence_pause_ms)
                combined += silence
                current_ms += sentence_pause_ms

    # Export MP3
    if len(combined) > 0:
        combined.export(str(output_mp3), format="mp3")
    else:
        # Export a minimal silent file
        AudioSegment.silent(duration=100).export(str(output_mp3), format="mp3")

    # Write timing JSON
    with open(timing_json, "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=2)

    duration_s = len(combined) / 1000.0
    logger.info(
        "Stitched %d sentences → %s (%.1fs)",
        idx, output_mp3.name, duration_s,
    )
    return duration_s, timing
