"""SQLAlchemy ORM models for Awaaz-e-Ilm.

Uses SQLAlchemy 2.0 `Mapped` / `mapped_column` declarative style.
All 7 tables are defined here and imported by Alembic env.py for migrations.

Tables
------
users           – registered platform users
documents       – uploaded PDF / EPUB / image documents
chapters        – individual sections within a document
audio_tracks    – synthesised audio files per chapter per language
playback_state  – last-known playback position per user+document
jobs            – async processing pipeline progress tracking
command_log     – voice-command audit trail
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracting = "extracting"
    ready = "ready"
    failed = "failed"


class ChapterStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(Base):
    """Platform user — may be the default single user in single-user mode."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="Default User")
    preferred_lang: Mapped[str] = mapped_column(String(10), default="en")
    speech_rate: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    documents: Mapped[list[Document]] = relationship(back_populates="user")
    playback_states: Mapped[list[PlaybackState]] = relationship(back_populates="user")
    command_logs: Mapped[list[CommandLog]] = relationship(back_populates="user")


class Document(Base):
    """Uploaded source document (PDF, EPUB, image, etc.)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(32))
    source_lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.uploaded
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[User] = relationship(back_populates="documents")
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    playback_states: Mapped[list[PlaybackState]] = relationship(back_populates="document")


class Chapter(Base):
    """A single chapter / section extracted from a Document."""

    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512))
    text_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    lang: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[ChapterStatus] = mapped_column(
        SAEnum(ChapterStatus), default=ChapterStatus.pending
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="chapters")
    audio_tracks: Mapped[list[AudioTrack]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )


class AudioTrack(Base):
    """A synthesised audio file for a Chapter in a specific language."""

    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), nullable=False)
    lang: Mapped[str] = mapped_column(String(10))
    voice: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audio_path: Mapped[str] = mapped_column(String(1024))
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    timing_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    chapter: Mapped[Chapter] = relationship(back_populates="audio_tracks")


class PlaybackState(Base):
    """Persisted playback position for a user+document pair."""

    __tablename__ = "playback_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    chapter_index: Mapped[int] = mapped_column(Integer, default=0)
    position_s: Mapped[float] = mapped_column(Float, default=0.0)
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    audio_lang: Mapped[str] = mapped_column(String(10), default="en")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="playback_states")
    document: Mapped[Document] = relationship(back_populates="playback_states")


class Job(Base):
    """Background pipeline job for a document (ingestion, TTS, etc.)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(64))
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="jobs")


class CommandLog(Base):
    """Audit log for every voice command received from a user."""

    __tablename__ = "command_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    transcript: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[User] = relationship(back_populates="command_logs")
