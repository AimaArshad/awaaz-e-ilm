"""Audio generation orchestrator.

Coordinates text preparation, TTS synthesis, stitching, and DB persistence
for a single chapter.  Runs synthesis sentence-by-sentence on a thread-pool
so the FastAPI event loop stays responsive.

Public API
----------
``generate_chapter_audio(chapter_id, lang, force)``
    Call from a ``BackgroundTasks`` callback or thread.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from pydub import AudioSegment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AudioTrack, Chapter, ChapterStatus
from app.services.audio_stitch import stitch_and_export
from app.services.tts.base import TTSEngine, get_engine
from app.services.tts_text import Paragraph, prepare_for_speech

logger = logging.getLogger(__name__)

# Thread-pool for CPU-bound synthesis
_synth_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tts")


# ---------------------------------------------------------------------------
# Hash for cache invalidation
# ---------------------------------------------------------------------------

def _content_hash(cleaned_text: str, voice: str, engine_version: str) -> str:
    """SHA-256 of (cleaned text + voice + engine version)."""
    h = hashlib.sha256()
    h.update(cleaned_text.encode("utf-8"))
    h.update(voice.encode("utf-8"))
    h.update(engine_version.encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Synthesis helpers (synchronous — run in thread-pool)
# ---------------------------------------------------------------------------

def _synthesize_paragraphs(
    engine: TTSEngine,
    paragraphs: List[Paragraph],
    lang: str,
) -> List[List[AudioSegment]]:
    """Synthesise all sentences, returning nested AudioSegments."""
    result: List[List[AudioSegment]] = []
    for para in paragraphs:
        clips: list[AudioSegment] = []
        for sentence in para:
            try:
                clip = engine.synthesize(sentence, lang=lang)
                clips.append(clip)
            except Exception:
                logger.exception("Synthesis failed for sentence: %s...", sentence[:60])
                # Insert 500ms silence as placeholder
                clips.append(AudioSegment.silent(duration=500))
        result.append(clips)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def generate_chapter_audio(
    chapter_id: int,
    lang: str = "en",
    force: bool = False,
    engine_override: Optional[TTSEngine] = None,
    session_factory=None,
) -> dict:
    """..."""  # keep your docstring
    if session_factory is None:
        from app.db.session import AsyncSessionLocal
        session_factory = AsyncSessionLocal

    settings = get_settings()

    async with session_factory() as db:
        try:
            return await _generate(db, chapter_id, lang, force, engine_override, settings)
        # ... rest unchanged
# async def generate_chapter_audio(
#     chapter_id: int,
#     lang: str = "en",
#     force: bool = False,
#     engine_override: Optional[TTSEngine] = None,
# ) -> dict:
#     """Generate (or return cached) audio for a chapter.

#     Args:
#         chapter_id: DB id of the Chapter.
#         lang: Language code for synthesis.
#         force: If True, regenerate even if cached.
#         engine_override: Optional engine to use instead of the registry
#                          (used by tests with a fake engine).

#     Returns:
#         Dict with keys: status, audio_path, timing_path, duration_s, truncated, error.
#     """
#     from app.db.session import AsyncSessionLocal

#     settings = get_settings()

#     async with AsyncSessionLocal() as db:
#         try:
#             return await _generate(db, chapter_id, lang, force, engine_override, settings)
        except Exception as exc:
            logger.exception("Audio generation failed for chapter %d", chapter_id)
            # Record error in DB
            try:
                await _set_track_error(db, chapter_id, lang, str(exc))
            except Exception:
                pass
            return {
                "status": "failed",
                "audio_path": None,
                "timing_path": None,
                "duration_s": None,
                "truncated": False,
                "error": str(exc),
            }


async def _set_track_error(db: AsyncSession, chapter_id: int, lang: str, error: str):
    """Record an error on an existing track or create an error track."""
    result = await db.execute(
        select(AudioTrack).where(
            AudioTrack.chapter_id == chapter_id,
            AudioTrack.lang == lang,
        )
    )
    track = result.scalar_one_or_none()
    if track:
        track.status = "failed"
        track.error = error
    else:
        track = AudioTrack(
            chapter_id=chapter_id,
            lang=lang,
            audio_path="",
            status="failed",
            error=error,
        )
        db.add(track)

    # Update chapter status
    ch_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = ch_result.scalar_one_or_none()
    if ch:
        ch.status = ChapterStatus.failed
    await db.commit()


async def _generate(
    db: AsyncSession,
    chapter_id: int,
    lang: str,
    force: bool,
    engine_override: Optional[TTSEngine],
    settings,
) -> dict:
    """Core generation logic."""
    # Load chapter
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        return {"status": "failed", "error": f"Chapter {chapter_id} not found",
                "audio_path": None, "timing_path": None, "duration_s": None, "truncated": False}

    # Read chapter text
    if not chapter.text_path:
        return {"status": "failed", "error": "Chapter has no text",
                "audio_path": None, "timing_path": None, "duration_s": None, "truncated": False}

    text_path = Path(chapter.text_path)
    if not text_path.exists():
        return {"status": "failed", "error": f"Text file not found: {text_path}",
                "audio_path": None, "timing_path": None, "duration_s": None, "truncated": False}

    chapter_text = text_path.read_text(encoding="utf-8")

    # Get engine
    engine = engine_override or get_engine(lang)
    voice = settings.piper_voice if lang == "en" else "default"

    # Prepare text
    prepared = prepare_for_speech(chapter_text, lang=lang)
    if not prepared.paragraphs:
        return {"status": "failed", "error": "No speakable text after cleanup",
                "audio_path": None, "timing_path": None, "duration_s": None, "truncated": False}

    # Build cleaned text string for hashing
    cleaned_flat = " ".join(
        sent for para in prepared.paragraphs for sent in para
    )
    chash = _content_hash(cleaned_flat, voice, engine.ENGINE_VERSION)

    # Check cache
    if not force:
        existing = await db.execute(
            select(AudioTrack).where(
                AudioTrack.chapter_id == chapter_id,
                AudioTrack.lang == lang,
                AudioTrack.content_hash == chash,
                AudioTrack.status == "ready",
            )
        )
        cached = existing.scalar_one_or_none()
        if cached:
            logger.info("Cache hit for chapter %d lang=%s", chapter_id, lang)
            return {
                "status": "ready",
                "audio_path": cached.audio_path,
                "timing_path": cached.timing_path,
                "duration_s": cached.duration_s,
                "truncated": cached.truncated,
                "error": None,
            }

    # Mark chapter as processing
    chapter.status = ChapterStatus.processing
    await db.commit()

    # Set up output paths
    audio_dir = Path(settings.storage_dir) / "audio" / str(chapter.document_id)
    mp3_path = audio_dir / f"chapter_{chapter.index}_{lang}.mp3"
    timing_path = audio_dir / f"chapter_{chapter.index}_{lang}.timing.json"

    # Run synthesis in thread-pool
    loop = asyncio.get_event_loop()
    para_clips = await loop.run_in_executor(
        _synth_pool,
        _synthesize_paragraphs,
        engine,
        prepared.paragraphs,
        lang,
    )

    # Stitch and export
    duration_s, timing_data = await loop.run_in_executor(
        _synth_pool,
        stitch_and_export,
        para_clips,
        prepared.paragraphs,
        mp3_path,
        timing_path,
    )

    # Upsert AudioTrack
    existing_result = await db.execute(
        select(AudioTrack).where(
            AudioTrack.chapter_id == chapter_id,
            AudioTrack.lang == lang,
        )
    )
    track = existing_result.scalar_one_or_none()
    if track:
        track.audio_path = str(mp3_path)
        track.timing_path = str(timing_path)
        track.duration_s = duration_s
        track.voice = voice
        track.content_hash = chash
        track.truncated = prepared.truncated
        track.status = "ready"
        track.error = None
    else:
        track = AudioTrack(
            chapter_id=chapter_id,
            lang=lang,
            voice=voice,
            audio_path=str(mp3_path),
            timing_path=str(timing_path),
            duration_s=duration_s,
            content_hash=chash,
            truncated=prepared.truncated,
            status="ready",
        )
        db.add(track)

    # Update chapter status
    chapter.status = ChapterStatus.ready
    await db.commit()

    logger.info(
        "Audio generated for chapter %d lang=%s: %.1fs, truncated=%s",
        chapter_id, lang, duration_s, prepared.truncated,
    )

    return {
        "status": "ready",
        "audio_path": str(mp3_path),
        "timing_path": str(timing_path),
        "duration_s": duration_s,
        "truncated": prepared.truncated,
        "error": None,
    }

