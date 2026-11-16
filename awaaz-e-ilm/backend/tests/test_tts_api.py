"""Tests for the TTS API endpoints and audio generation pipeline.

Uses a fake TTSEngine that returns short silent audio, so the suite
does not need actual Piper models and stays fast.

Also includes a real-Piper test marked @pytest.mark.slow that is
skipped if the voice file is missing.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydub import AudioSegment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AudioTrack, Base, Chapter, ChapterStatus, Document, DocumentStatus, User
from app.db.session import get_db
from app.main import app
from app.services.tts.base import TTSEngine, register_engine, reset_engines, _REGISTRY, _INSTANCES

from tests.conftest import TestSessionLocal, test_engine


# ===========================================================================
# Fake TTS engine for testing
# ===========================================================================

class FakeTTSEngine(TTSEngine):
    """Returns a short 200ms tone (440 Hz) or silence for testing."""

    ENGINE_VERSION = "fake-1.0"
    call_count = 0

    def synthesize(self, text: str, lang: str = "en") -> AudioSegment:
        FakeTTSEngine.call_count += 1
        # Generate a 200ms silent clip (fast, no model needed)
        return AudioSegment.silent(duration=200, frame_rate=22050)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest_asyncio.fixture
async def setup_test_db():
    """Create tables and seed data for TTS tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        # Ensure default user exists
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            user = User(name="Test User", preferred_lang="en", speech_rate=1.0)
            session.add(user)
            await session.flush()

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_with_chapter(setup_test_db, tmp_path):
    """Create a document and chapter with text in tmp storage."""
    session = setup_test_db

    # Get user
    result = await session.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    # Create document
    doc = Document(
        user_id=user.id,
        title="Test Physics Book",
        filename="test.pdf",
        file_type="pdf",
        status=DocumentStatus.ready,
    )
    session.add(doc)
    await session.flush()

    # Write chapter text to a file
    text_dir = tmp_path / "text" / str(doc.id)
    text_dir.mkdir(parents=True)
    text_path = text_dir / "chapter_0.txt"
    text_path.write_text(
        "Chapter 1: Introduction to Physics\n\n"
        "Physics is the study of matter and energy. "
        "It explores the fundamental forces of nature.\n\n"
        "The speed of light is approximately 300000 km/h. "
        "Water boils at 100°C under normal atmospheric pressure.",
        encoding="utf-8",
    )

    # Create chapter
    chapter = Chapter(
        document_id=doc.id,
        index=0,
        title="Chapter 1: Introduction to Physics",
        text_path=str(text_path),
        lang="en",
        status=ChapterStatus.ready,
    )
    session.add(chapter)
    await session.commit()
    await session.refresh(chapter)

    yield session, chapter, tmp_path


@pytest.fixture
def fake_engine():
    """Register and return a fake TTS engine, restoring the original after."""
    original_registry = dict(_REGISTRY)
    original_instances = dict(_INSTANCES)

    FakeTTSEngine.call_count = 0
    register_engine("en", FakeTTSEngine)
    reset_engines()

    yield FakeTTSEngine()

    _REGISTRY.clear()
    _REGISTRY.update(original_registry)
    _INSTANCES.clear()
    _INSTANCES.update(original_instances)


@pytest_asyncio.fixture
async def client(setup_test_db):
    """Async HTTPX client wired to the FastAPI app."""
    async def _override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# Unit tests: FakeTTSEngine
# ===========================================================================

class TestFakeTTSEngine:
    def test_synthesize_returns_audio(self):
        engine = FakeTTSEngine()
        result = engine.synthesize("Hello world", lang="en")
        assert isinstance(result, AudioSegment)
        assert len(result) > 0  # duration in ms

    def test_engine_version(self):
        engine = FakeTTSEngine()
        assert engine.ENGINE_VERSION == "fake-1.0"


# ===========================================================================
# Integration tests: audio generation
# ===========================================================================

class TestAudioGeneration:
    @pytest.mark.asyncio
    async def test_generate_chapter_audio(self, db_with_chapter, fake_engine, monkeypatch):
        """Generate audio for a chapter using the fake engine."""
        session, chapter, tmp_path = db_with_chapter

        monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
        from app.config import get_settings
        get_settings.cache_clear()

        try:
            from app.services.audio_generation import generate_chapter_audio
            result = await generate_chapter_audio(
                chapter.id, lang="en", force=False, engine_override=fake_engine,
            session_factory=TestSessionLocal)

            assert result["status"] == "ready"
            assert result["error"] is None
            assert result["duration_s"] > 0
            assert Path(result["audio_path"]).exists()
            assert Path(result["timing_path"]).exists()

            # Check timing JSON
            with open(result["timing_path"], "r") as f:
                timing = json.load(f)
            assert len(timing) > 0
            assert timing[0]["idx"] == 0
            assert timing[0]["start_s"] == 0.0
            assert timing[0]["end_s"] > 0
            assert isinstance(timing[0]["text"], str)
        finally:
            get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_cache_prevents_regeneration(self, db_with_chapter, fake_engine, monkeypatch):
        """Second call with same text should hit the cache."""
        session, chapter, tmp_path = db_with_chapter

        monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
        from app.config import get_settings
        get_settings.cache_clear()

        try:
            from app.services.audio_generation import generate_chapter_audio

            # First call — generates
            FakeTTSEngine.call_count = 0
            result1 = await generate_chapter_audio(
                chapter.id, lang="en", force=False, engine_override=fake_engine,
      session_factory=TestSessionLocal            )
            first_call_count = FakeTTSEngine.call_count
            assert first_call_count > 0

            # Second call — should hit cache
            FakeTTSEngine.call_count = 0
            result2 = await generate_chapter_audio(
                chapter.id, lang="en", force=False, engine_override=fake_engine,
            session_factory=TestSessionLocal)
            assert FakeTTSEngine.call_count == 0, "Cache should prevent re-synthesis"
            assert result2["status"] == "ready"
            assert result2["duration_s"] == result1["duration_s"]
        finally:
            get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_force_regenerates(self, db_with_chapter, fake_engine, monkeypatch):
        """force=True should regenerate even if cached."""
        session, chapter, tmp_path = db_with_chapter

        monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
        from app.config import get_settings
        get_settings.cache_clear()

        try:
            from app.services.audio_generation import generate_chapter_audio

            # First call
            await generate_chapter_audio(
                chapter.id, lang="en", force=False, engine_override=fake_engine,session_factory=TestSessionLocal
            )

            # Force regeneration
            FakeTTSEngine.call_count = 0
            result = await generate_chapter_audio(
                chapter.id, lang="en", force=True, engine_override=fake_engine,session_factory=TestSessionLocal
            )
            assert FakeTTSEngine.call_count > 0, "Force should regenerate"
            assert result["status"] == "ready"
        finally:
            get_settings.cache_clear()


# ===========================================================================
# Real Piper test (slow, skipped if model missing)
# ===========================================================================

class TestRealPiper:
    @pytest.mark.slow
    def test_piper_synthesize_one_sentence(self):
        """Synthesise one sentence with the real Piper engine.

        Skipped if the voice model file is not found.
        """
        from app.config import get_settings
        settings = get_settings()
        model_path = Path(settings.models_cache_dir) / "piper" / f"{settings.piper_voice}.onnx"

        if not model_path.exists():
            pytest.skip(
                f"Piper voice model not found at {model_path}. "
                f"Run: python scripts/download_models.py"
            )

        from app.services.tts.piper_en import PiperEnglishEngine
        engine = PiperEnglishEngine()
        result = engine.synthesize("This is a test of the English voice.", lang="en")

        assert isinstance(result, AudioSegment)
        assert len(result) > 0, "Audio duration should be > 0"
        duration_s = len(result) / 1000.0
        assert duration_s > 0.5, f"Expected > 0.5s, got {duration_s:.2f}s"

