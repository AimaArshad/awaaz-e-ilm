"""Pydantic v2 request/response schemas for all API endpoints.

All read schemas use `model_config = ConfigDict(from_attributes=True)` so
SQLAlchemy ORM objects can be passed directly to `model_validate()`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.db.models import ChapterStatus, DocumentStatus


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    name: str = "Default User"
    preferred_lang: str = "en"
    speech_rate: float = 1.0


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    preferred_lang: Optional[str] = None
    speech_rate: Optional[float] = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    title: str
    source_lang: Optional[str] = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    filename: str
    file_type: str
    source_lang: Optional[str]
    status: DocumentStatus
    created_at: datetime


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------

class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    index: int
    title: str
    text_path: Optional[str]
    lang: str
    status: ChapterStatus


# ---------------------------------------------------------------------------
# Audio Track
# ---------------------------------------------------------------------------

class AudioTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_id: int
    lang: str
    voice: Optional[str]
    audio_path: str
    duration_s: Optional[float]
    timing_path: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Playback State
# ---------------------------------------------------------------------------

class PlaybackStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    document_id: int
    chapter_index: int
    position_s: float
    speed: float
    audio_lang: str
    updated_at: datetime


class PlaybackStateUpdate(BaseModel):
    chapter_index: Optional[int] = None
    position_s: Optional[float] = None
    speed: Optional[float] = None
    audio_lang: Optional[str] = None


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    stage: str
    progress: float
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
