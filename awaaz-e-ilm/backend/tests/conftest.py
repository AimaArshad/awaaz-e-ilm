"""Pytest fixtures shared across all backend tests.

Provides:
- ``test_engine`` / ``TestSessionLocal``: in-memory SQLite for fast tests.
- ``db``: async DB session with automatic rollback.
- ``async_client``: HTTPX AsyncClient wired to the FastAPI app.
- Fixture generators for sample PDF, DOCX, and image files.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, User
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# DB lifecycle fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Create all tables once per test session and seed a default user."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default user
    async with TestSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            session.add(User(name="Test User", preferred_lang="en", speech_rate=1.0))
            await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db):
    """Yield an async DB session for a single test."""
    async with TestSessionLocal() as session:
        yield session


async def _override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def async_client(setup_db):
    """Async HTTPX client wired to the FastAPI app with DB override."""
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Event loop  (required for session-scoped async fixtures)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Temporary directory for test storage
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    """Override STORAGE_DIR to a temp directory for the test."""
    storage = str(tmp_path / "storage")
    os.makedirs(storage, exist_ok=True)
    monkeypatch.setenv("STORAGE_DIR", storage)
    return storage


# ---------------------------------------------------------------------------
# Test fixture files
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="session")
def english_pdf_path() -> str:
    """Path to a sample English PDF with a text layer."""
    import fitz

    path = os.path.join(FIXTURES_DIR, "sample_english.pdf")
    if os.path.isfile(path):
        return path

    os.makedirs(FIXTURES_DIR, exist_ok=True)
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text(
        (72, 100),
        "Chapter 1\n\nThis is a sample English document for testing the text "
        "extraction pipeline. It contains multiple paragraphs of text.\n\n"
        "The quick brown fox jumps over the lazy dog.",
        fontsize=12,
    )
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text(
        (72, 100),
        "Chapter 2\n\nThis is the second chapter. "
        "It tests chapter detection and multi-page extraction.",
        fontsize=12,
    )
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="session")
def scanned_pdf_path() -> str:
    """Path to a PDF with no text layer (image-only, simulated scan)."""
    import fitz
    from PIL import Image, ImageDraw, ImageFont

    path = os.path.join(FIXTURES_DIR, "sample_scanned.pdf")
    if os.path.isfile(path):
        return path

    os.makedirs(FIXTURES_DIR, exist_ok=True)

    # Render text to an image
    img = Image.new("RGB", (612, 792), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for i, line in enumerate([
        "This is a scanned page.",
        "The text is embedded in an image.",
        "OCR is required to extract this text.",
    ]):
        draw.text((72, 100 + i * 30), line, fill="black", font=font)

    img_path = path.replace(".pdf", "_temp.png")
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(0, 0, 612, 792), filename=img_path)
    doc.save(path)
    doc.close()
    os.remove(img_path)
    return path


@pytest.fixture(scope="session")
def english_docx_path() -> str:
    """Path to a sample DOCX with English text."""
    from docx import Document

    path = os.path.join(FIXTURES_DIR, "sample_english.docx")
    if os.path.isfile(path):
        return path

    os.makedirs(FIXTURES_DIR, exist_ok=True)
    doc = Document()
    doc.add_heading("Chapter 1: Introduction", level=1)
    doc.add_paragraph(
        "This is a test DOCX document for the text extraction service. "
        "It contains multiple paragraphs to test extraction."
    )
    doc.add_heading("Chapter 2: Methods", level=1)
    doc.add_paragraph(
        "This chapter covers the methodology. "
        "Various techniques were employed."
    )
    doc.save(path)
    return path


@pytest.fixture(scope="session")
def english_image_path() -> str:
    """Path to a PNG image with English text for OCR testing."""
    from PIL import Image, ImageDraw, ImageFont

    path = os.path.join(FIXTURES_DIR, "sample_english.png")
    if os.path.isfile(path):
        return path

    os.makedirs(FIXTURES_DIR, exist_ok=True)
    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text((40, 40), "The quick brown fox jumps over the lazy dog.", fill="black", font=font)
    draw.text((40, 100), "Testing OCR extraction pipeline.", fill="black", font=font)
    img.save(path)
    return path


@pytest.fixture(scope="session")
def urdu_image_path() -> str:
    """Path to a PNG image with Urdu text for OCR testing."""
    from PIL import Image, ImageDraw, ImageFont

    path = os.path.join(FIXTURES_DIR, "sample_urdu.png")
    if os.path.isfile(path):
        return path

    os.makedirs(FIXTURES_DIR, exist_ok=True)
    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)

    font = None
    for font_name in ["Jameel Noori Nastaleeq.ttf", "NotoNastaliqUrdu-Regular.ttf", "arial.ttf"]:
        try:
            font = ImageFont.truetype(font_name, 28)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    draw.text((40, 40), "یہ اردو زبان کا ایک ٹیسٹ ہے۔", fill="black", font=font)
    img.save(path)
    return path


@pytest.fixture(scope="session")
def jpg_image_path(english_image_path) -> str:
    """Path to a JPG image (converted from the English PNG)."""
    from PIL import Image

    path = os.path.join(FIXTURES_DIR, "sample_english.jpg")
    if os.path.isfile(path):
        return path

    img = Image.open(english_image_path)
    img.convert("RGB").save(path, "JPEG")
    return path
