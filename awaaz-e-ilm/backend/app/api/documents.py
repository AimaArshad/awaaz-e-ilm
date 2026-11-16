"""Documents API router.

Endpoints
---------
GET  /documents/              List all documents for the default user
POST /documents/              Upload a new document (multipart/form-data)
GET  /documents/{id}          Retrieve a single document
DELETE /documents/{id}        Delete a document and its chapters
GET  /documents/{id}/chapters List chapters for a document

Accepted file types: PDF, DOCX, PNG, JPG/JPEG.
"""
import os
import shutil
from typing import List

import aiofiles
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Chapter, Document, DocumentStatus, Job, User
from app.db.schemas import ChapterRead, DocumentRead
from app.db.session import get_db
from app.services.text_extract import SUPPORTED_EXTENSIONS
from app.utils.file_utils import ensure_dir

router = APIRouter()
settings = get_settings()

# File types accepted by the upload endpoint
_ALLOWED_EXTENSIONS = frozenset(SUPPORTED_EXTENSIONS.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_default_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=500, detail="No default user found")
    return user


async def _get_document_or_404(doc_id: int, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ---------------------------------------------------------------------------
# Background ingestion task
# ---------------------------------------------------------------------------

async def _run_ingestion_pipeline(doc_id: int) -> None:
    """Background task that runs the full ingestion pipeline.

    Uses :func:`app.services.ingestion.ingest_document` which handles
    extraction, OCR, language detection, cleanup, and chapter splitting.
    """
    from app.services.ingestion import ingest_document
    await ingest_document(doc_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[DocumentRead])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Return all documents belonging to the default user."""
    user = await _get_default_user(db)
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document file and queue it for processing.

    Accepts **PDF**, **DOCX**, **PNG**, **JPG/JPEG**.
    The file is saved to ``{STORAGE_DIR}/uploads/{document_id}/{filename}``
    and a background ingestion pipeline is started.
    """
    user = await _get_default_user(db)

    # ── Validate file type ─────────────────────────────────────────────────
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type: '.{ext}'. "
                f"Accepted: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
            ),
        )

    # ── Create Document record ─────────────────────────────────────────────
    doc_title = title.strip() or os.path.splitext(filename)[0]
    doc = Document(
        user_id=user.id,
        title=doc_title,
        filename=filename,
        file_type=ext,
        status=DocumentStatus.uploaded,
    )
    db.add(doc)
    await db.flush()  # get doc.id

    # ── Save uploaded file to storage ──────────────────────────────────────
    upload_dir = os.path.join(settings.storage_dir, "uploads", str(doc.id))
    ensure_dir(upload_dir)
    dest_path = os.path.join(upload_dir, filename)

    async with aiofiles.open(dest_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            await out.write(chunk)

    # ── Create tracking Job ────────────────────────────────────────────────
    job = Job(document_id=doc.id, stage="queued", progress=0.0)
    db.add(job)
    await db.commit()
    await db.refresh(doc)

    # ── Kick off ingestion pipeline ────────────────────────────────────────
    background_tasks.add_task(_run_ingestion_pipeline, doc.id)

    return doc


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a single document by ID."""
    return await _get_document_or_404(doc_id, db)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a document and its related data from the DB and storage."""
    doc = await _get_document_or_404(doc_id, db)

    # Remove stored files
    for subdir in ("uploads", "pages", "text", "audio"):
        dir_path = os.path.join(settings.storage_dir, subdir, str(doc.id))
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)

    await db.delete(doc)
    await db.commit()


@router.get("/{doc_id}/chapters", response_model=List[ChapterRead])
async def list_chapters(doc_id: int, db: AsyncSession = Depends(get_db)):
    """List all chapters for a document, ordered by chapter index."""
    await _get_document_or_404(doc_id, db)
    result = await db.execute(
        select(Chapter)
        .where(Chapter.document_id == doc_id)
        .order_by(Chapter.index)
    )
    return result.scalars().all()
