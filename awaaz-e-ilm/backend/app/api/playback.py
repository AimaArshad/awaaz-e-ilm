"""Playback state API router.

Endpoints
---------
GET /playback/{document_id}  Get last playback position for the default user
PUT /playback/{document_id}  Save / update playback position

The frontend polls or pushes playback state here so users resume exactly
where they left off — even after closing the browser.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, PlaybackState, User
from app.db.schemas import PlaybackStateRead, PlaybackStateUpdate
from app.db.session import get_db

router = APIRouter()


async def _get_default_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=500, detail="No default user found")
    return user


@router.get("/{document_id}", response_model=PlaybackStateRead)
async def get_playback_state(document_id: int, db: AsyncSession = Depends(get_db)):
    """Return the saved playback state for a document.

    Creates a fresh state record (position 0) if none exists yet.
    """
    user = await _get_default_user(db)

    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(PlaybackState).where(
            PlaybackState.user_id == user.id,
            PlaybackState.document_id == document_id,
        )
    )
    state = result.scalar_one_or_none()

    if not state:
        # Create default state
        state = PlaybackState(
            user_id=user.id,
            document_id=document_id,
            chapter_index=0,
            position_s=0.0,
            speed=1.0,
            audio_lang=user.preferred_lang,
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)

    return state


@router.put("/{document_id}", response_model=PlaybackStateRead)
async def update_playback_state(
    document_id: int,
    payload: PlaybackStateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Persist the current playback position for a document."""
    user = await _get_default_user(db)

    result = await db.execute(
        select(PlaybackState).where(
            PlaybackState.user_id == user.id,
            PlaybackState.document_id == document_id,
        )
    )
    state = result.scalar_one_or_none()

    if not state:
        state = PlaybackState(user_id=user.id, document_id=document_id)
        db.add(state)

    # Apply partial updates
    if payload.chapter_index is not None:
        state.chapter_index = payload.chapter_index
    if payload.position_s is not None:
        state.position_s = payload.position_s
    if payload.speed is not None:
        state.speed = payload.speed
    if payload.audio_lang is not None:
        state.audio_lang = payload.audio_lang

    await db.commit()
    await db.refresh(state)
    return state
