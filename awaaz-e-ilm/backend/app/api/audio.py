"""Audio API router.

Endpoints
---------
POST /chapters/{id}/audio?lang=en&force=false   Start generation
GET  /chapters/{id}/audio?lang=en               Stream MP3 (Range support)
GET  /chapters/{id}/timing?lang=en              Return timing JSON
GET  /chapters/{id}/audio/status?lang=en        Return status object
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AudioTrack, Chapter
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_chapter_or_404(chapter_id: int, db: AsyncSession) -> Chapter:
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


async def _get_track(chapter_id: int, lang: str, db: AsyncSession) -> AudioTrack | None:
    result = await db.execute(
        select(AudioTrack).where(
            AudioTrack.chapter_id == chapter_id,
            AudioTrack.lang == lang,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------
async def _run_audio_generation(chapter_id: int, lang: str, force: bool):
    from app.services.audio_generation import generate_chapter_audio
    try:
        await generate_chapter_audio(chapter_id, lang=lang, force=force)
    except Exception:
        logger.exception("Audio generation failed for chapter %s", chapter_id)
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            track = await _get_track(chapter_id, lang, db)
            if track and track.status == "processing":
                track.status = "failed"
                track.error = "Generation crashed; retry with force=true"
                await db.commit()

# async def _run_audio_generation(chapter_id: int, lang: str, force: bool):
#     """Background task wrapper."""
#     from app.services.audio_generation import generate_chapter_audio
#     await generate_chapter_audio(chapter_id, lang=lang, force=force)


# ---------------------------------------------------------------------------
# POST /chapters/{chapter_id}/audio
# ---------------------------------------------------------------------------

@router.post("/chapters/{chapter_id}/audio")
async def request_chapter_audio(
    chapter_id: int,
    background_tasks: BackgroundTasks,
    lang: str = Query("en"),
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Start audio generation for a chapter.

    Returns immediately with a status object.
    """
    chapter = await _get_chapter_or_404(chapter_id, db)
    track = await _get_track(chapter_id, lang, db)

    # If already ready and not forcing regeneration, return immediately
    if track and track.status == "ready" and not force:
        return {
            "status": "ready",
            "duration_s": track.duration_s,
            "truncated": track.truncated,
            "error": None,
        }

    # Mark as processing
    if track:
        track.status = "processing"
        track.error = None
        await db.commit()
    else:
        track = AudioTrack(
            chapter_id=chapter_id,
            lang=lang,
            audio_path="",
            status="processing",
        )
        db.add(track)
        await db.commit()

    # Kick off generation in background
    background_tasks.add_task(_run_audio_generation, chapter_id, lang, force)

    return {
        "status": "processing",
        "duration_s": None,
        "truncated": False,
        "error": None,
    }


# ---------------------------------------------------------------------------
# GET /chapters/{chapter_id}/audio
# ---------------------------------------------------------------------------

@router.get("/chapters/{chapter_id}/audio")
async def get_chapter_audio(
    chapter_id: int,
    request: Request,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_db),
):
    """Stream the MP3 file when ready, 202 while processing, 404 if never requested.

    Supports HTTP Range requests for seeking in the browser.
    """
    await _get_chapter_or_404(chapter_id, db)
    track = await _get_track(chapter_id, lang, db)

    if not track:
        raise HTTPException(status_code=404, detail="Audio not requested yet")

    if track.status == "processing":
        return JSONResponse(
            status_code=202,
            content={
                "status": "processing",
                "detail": "Audio is being generated",
            },
        )

    if track.status == "failed":
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "error": track.error or "Unknown error",
            },
        )

    # Status is "ready" — serve the file
    audio_path = Path(track.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    file_size = audio_path.stat().st_size

    # Handle Range requests
    range_header = request.headers.get("range")
    if range_header:
        try:
            range_spec = range_header.strip().lower()
            if range_spec.startswith("bytes="):
                range_spec = range_spec[6:]
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

            if start >= file_size:
                return Response(
                    status_code=416,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )

            end = min(end, file_size - 1)
            content_length = end - start + 1

            with open(audio_path, "rb") as f:
                f.seek(start)
                data = f.read(content_length)

            return Response(
                content=data,
                status_code=206,
                media_type="audio/mpeg",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                    "Accept-Ranges": "bytes",
                },
            )
        except (ValueError, IndexError):
            pass  # Fall through to normal response

    # Full file response
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"},
    )


# ---------------------------------------------------------------------------
# GET /chapters/{chapter_id}/timing
# ---------------------------------------------------------------------------

@router.get("/chapters/{chapter_id}/timing")
async def get_chapter_timing(
    chapter_id: int,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_db),
):
    """Return the timing JSON for a chapter's audio."""
    await _get_chapter_or_404(chapter_id, db)
    track = await _get_track(chapter_id, lang, db)

    if not track or not track.timing_path:
        raise HTTPException(status_code=404, detail="Timing data not available")

    timing_path = Path(track.timing_path)
    if not timing_path.exists():
        raise HTTPException(status_code=404, detail="Timing file not found on disk")

    with open(timing_path, "r", encoding="utf-8") as f:
        timing_data = json.load(f)

    return timing_data


# ---------------------------------------------------------------------------
# GET /chapters/{chapter_id}/audio/status
# ---------------------------------------------------------------------------

@router.get("/chapters/{chapter_id}/audio/status")
async def get_audio_status(
    chapter_id: int,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_db),
):
    """Return the current audio generation status for a chapter."""
    await _get_chapter_or_404(chapter_id, db)
    track = await _get_track(chapter_id, lang, db)

    if not track:
        raise HTTPException(status_code=404, detail="Audio not requested yet")

    return {
        "status": track.status,
        "duration_s": track.duration_s,
        "truncated": track.truncated,
        "error": track.error,
    }
