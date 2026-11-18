"""FastAPI application entry point.

Initialises the database on startup (dev convenience — production should
rely solely on `alembic upgrade head`), seeds a default user if none exists,
registers all API routers, and mounts CORS middleware.
"""


import asyncio
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import audio, chapters, documents, playback, voice_ws
from app.config import get_settings
from app.db.models import Base, User
from app.db.session import AsyncSessionLocal, engine


from sqlalchemy import select, update
from app.db.models import AudioTrack, Base, Chapter, ChapterStatus, User

settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed default user on startup."""
    # Create all tables (dev shortcut; Alembic handles prod migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed the default user if the table is empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            session.add(User(name="Default User", preferred_lang="en", speech_rate=1.0))
            await session.commit()
    
     # A restart kills in-flight generations; don't leave them "processing" forever
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(AudioTrack).where(AudioTrack.status == "processing")
            .values(status="failed", error="Interrupted by a server restart")
        )
        await session.execute(
            update(Chapter).where(Chapter.status == ChapterStatus.processing)
            .values(status=ChapterStatus.ready)
        )
        await session.commit()
    
            
    if settings.whisper_preload:
        from app.services import stt
        asyncio.get_running_loop().run_in_executor(None, stt.preload)
    yield  # application runs here

    # Cleanup (close connection pool)
    await engine.dispose()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Awaaz-e-Ilm API",
    version="0.1.0",
    description="Voice-controlled audiobook platform for visually impaired students.",
    lifespan=lifespan,
)

# CORS — allow all origins in dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chapters.router, prefix="/chapters", tags=["chapters"])
app.include_router(audio.router, tags=["audio"])
app.include_router(playback.router, prefix="/playback", tags=["playback"])
app.include_router(voice_ws.router, tags=["voice"])


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"], response_model=dict)
async def health():
    """Health-check endpoint.  Returns 200 with basic info."""
    return {"status": "ok", "version": "0.1.0"}





FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"   # <repo>/frontend
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")