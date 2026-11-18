"""Start / track audio generation outside of FastAPI BackgroundTasks.

Used by the voice commands (and by the REST endpoint). Single-process only:
run uvicorn with --workers 1.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AudioTrack

logger = logging.getLogger(__name__)

_tasks: set[asyncio.Task] = set()   # keep references so tasks are not garbage-collected


def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task


async def get_track(chapter_id: int, lang: str, db: AsyncSession) -> AudioTrack | None:
    result = await db.execute(
        select(AudioTrack).where(AudioTrack.chapter_id == chapter_id, AudioTrack.lang == lang)
    )
    return result.scalars().first()


async def run_generation(chapter_id: int, lang: str, force: bool = False) -> None:
    """Generate audio; if it fails for any reason, mark the track failed (never leave 'processing')."""
    from app.db.session import AsyncSessionLocal
    from app.services.audio_generation import generate_chapter_audio

    error = None
    try:
        result = await generate_chapter_audio(chapter_id, lang=lang, force=force)
        if result.get("status") == "failed":
            error = result.get("error") or "Generation failed"
    except Exception:
        logger.exception("Audio generation crashed for chapter %s", chapter_id)
        error = "Generation crashed; try again"

    if error:
        async with AsyncSessionLocal() as db:
            track = await get_track(chapter_id, lang, db)
            if track and track.status == "processing":
                track.status = "failed"
                track.error = error
                await db.commit()


async def ensure_audio(chapter_id: int, lang: str, db: AsyncSession) -> str:
    """Return 'ready' (cached, file exists), 'processing' (already running) or 'started'."""
    track = await get_track(chapter_id, lang, db)
    if track and track.status == "ready" and track.audio_path and Path(track.audio_path).is_file():
        return "ready"
    if track and track.status == "processing":
        return "processing"

    if track:
        track.status = "processing"
        track.error = None
    else:
        db.add(AudioTrack(chapter_id=chapter_id, lang=lang, audio_path="", status="processing"))
    await db.commit()

    spawn(run_generation(chapter_id, lang))
    logger.info("Started audio generation: chapter=%s lang=%s", chapter_id, lang)
    return "started"