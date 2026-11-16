"""Chapters API router.

Endpoints
---------
POST /chapters/{id}/regenerate  Trigger re-generation of a chapter's audio

Milestone notes
---------------
Milestone 3 will implement the actual TTS regeneration pipeline.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chapter
from app.db.schemas import ChapterRead
from app.db.session import get_db

router = APIRouter()


@router.post("/{chapter_id}/regenerate", response_model=ChapterRead)
async def regenerate_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    """Queue a chapter for TTS re-generation.

    Currently a stub — will trigger the TTS pipeline in Milestone 3.
    Returns the current chapter state.
    """
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # TODO (Milestone 3): enqueue TTS job via Celery or BackgroundTasks
    return chapter
