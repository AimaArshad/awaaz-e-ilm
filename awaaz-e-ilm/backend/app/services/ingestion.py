"""Document ingestion orchestrator.

Coordinates the full document processing pipeline:

    upload → extract → (OCR) → lang detect → cleanup → chapter split → DB

The pipeline runs as a FastAPI ``BackgroundTask`` (or Celery task when
``USE_CELERY=true``).  It updates the ``jobs`` table and emits WebSocket
progress events at each stage.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import (
    Chapter,
    ChapterStatus,
    Document,
    DocumentStatus,
    Job,
)
from app.services import text_extract, cleanup, lang_detect
from app.services.chapters import split_chapters
from app.utils.file_utils import ensure_dir

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

async def _update_job(
    db: AsyncSession,
    document_id: int,
    stage: str,
    progress: float,
    error: Optional[str] = None,
) -> None:
    """Update the Job record for a document."""
    result = await db.execute(
        select(Job).where(Job.document_id == document_id).limit(1)
    )
    job = result.scalar_one_or_none()
    if job:
        job.stage = stage
        job.progress = progress
        job.error = error
        await db.commit()


async def _stage_extract(
    db: AsyncSession,
    doc: Document,
    file_path: str,
) -> text_extract.ExtractionResult:
    """Stage 1: Text extraction."""
    await _update_job(db, doc.id, "extracting", 0.1)
    doc.status = DocumentStatus.extracting
    await db.commit()

    render_dir = os.path.join(settings.storage_dir, "pages", str(doc.id))
    ensure_dir(render_dir)

    extraction = text_extract.extract(file_path, render_dir=render_dir)
    logger.info(
        "Extracted %d pages from %s (%d need OCR)",
        len(extraction.pages),
        doc.filename,
        len(extraction.pages_needing_ocr),
    )
    return extraction


async def _stage_ocr(
    db: AsyncSession,
    doc: Document,
    extraction: text_extract.ExtractionResult,
) -> text_extract.ExtractionResult:
    """Stage 2: OCR for pages without a text layer."""
    pages_needing_ocr = extraction.pages_needing_ocr
    if not pages_needing_ocr:
        logger.info("No pages need OCR — skipping stage")
        return extraction

    await _update_job(db, doc.id, "ocr", 0.2)

    try:
        from app.services.ocr import run_ocr
    except ImportError as exc:
        logger.warning("OCR dependencies not available: %s", exc)
        return extraction

    total = len(pages_needing_ocr)
    for i, page in enumerate(pages_needing_ocr):
        if page.image_path and os.path.isfile(page.image_path):
            try:
                result = run_ocr(page.image_path, lang="en+ur")
                page.text = result.text
                page.needs_ocr = False
                logger.info(
                    "OCR page %d: %d chars (engine=%s, conf=%.1f)",
                    page.page_index, len(result.text),
                    result.engine, result.confidence or 0,
                )
            except Exception as exc:
                logger.error("OCR failed for page %d: %s", page.page_index, exc)

        # Update progress within the OCR stage (0.2 → 0.4)
        progress = 0.2 + (0.2 * (i + 1) / total)
        await _update_job(db, doc.id, "ocr", progress)

    return extraction


async def _stage_lang_detect_and_cleanup(
    db: AsyncSession,
    doc: Document,
    extraction: text_extract.ExtractionResult,
) -> str:
    """Stage 3: Language detection + text cleanup.

    Returns the cleaned, full document text.
    """
    await _update_job(db, doc.id, "cleanup", 0.5)

    full_text = extraction.full_text

    # Detect dominant language
    detected_lang = lang_detect.detect_language(full_text, default="en")
    doc.source_lang = detected_lang
    logger.info("Detected document language: %s", detected_lang)

    # Clean text
    cleaned = cleanup.clean_text(full_text, lang=detected_lang)
    logger.info("Cleaned text: %d → %d chars", len(full_text), len(cleaned))

    # Save full cleaned text to storage
    text_dir = os.path.join(settings.storage_dir, "text", str(doc.id))
    ensure_dir(text_dir)
    full_text_path = os.path.join(text_dir, "full_text.txt")
    with open(full_text_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    await db.commit()
    return cleaned


async def _stage_chapter_split(
    db: AsyncSession,
    doc: Document,
    cleaned_text: str,
    extraction: text_extract.ExtractionResult,
    file_path: str,
) -> list[Chapter]:
    """Stage 4: Split into chapters and persist to DB."""
    await _update_job(db, doc.id, "chapter_split", 0.6)

    # Build per-page text list for strategies that need it
    pages_text = [p.text for p in extraction.pages] if extraction.pages else None

    chapter_dicts = split_chapters(
        cleaned_text,
        file_path=file_path,
        pages_text=pages_text,
        file_type=extraction.file_type,
        default_lang=doc.source_lang or "en",
    )
    logger.info(
        "Split document into %d chapters (method: %s)",
        len(chapter_dicts),
        chapter_dicts[0].get("detection_method", "unknown") if chapter_dicts else "none",
    )

    chapters: list[Chapter] = []
    text_dir = os.path.join(settings.storage_dir, "text", str(doc.id))
    ensure_dir(text_dir)

    for ch_data in chapter_dicts:
        # Save chapter text to file
        ch_text_path = os.path.join(text_dir, f"chapter_{ch_data['index']}.txt")
        with open(ch_text_path, "w", encoding="utf-8") as f:
            f.write(ch_data["text"])

        # Use language from chapter detection (already detected per-chapter)
        ch_lang = ch_data.get("language", doc.source_lang or "en")

        chapter = Chapter(
            document_id=doc.id,
            index=ch_data["index"],
            title=ch_data["title"],
            text_path=ch_text_path,
            lang=ch_lang,
            status=ChapterStatus.ready,  # text is ready; audio comes in later milestone
        )
        db.add(chapter)
        chapters.append(chapter)

    await db.commit()
    return chapters


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def ingest_document(document_id: int) -> None:
    """Run the full ingestion pipeline for a document.

    This is the main entry point called from background tasks or Celery.
    It operates on a fresh DB session so it can commit independently.

    Args:
        document_id: ID of the Document record to process.
    """
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Load document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error("Document %d not found", document_id)
                return

            # Locate the uploaded file
            upload_dir = os.path.join(settings.storage_dir, "uploads", str(doc.id))
            file_path = os.path.join(upload_dir, doc.filename)
            if not os.path.isfile(file_path):
                logger.error("File not found: %s", file_path)
                await _update_job(db, doc.id, "failed", 0, error="Uploaded file not found")
                doc.status = DocumentStatus.failed
                await db.commit()
                return

            # ── Stage 1: Extract ───────────────────────────────────────────
            extraction = await _stage_extract(db, doc, file_path)

            # ── Stage 2: OCR ──────────────────────────────────────────────
            extraction = await _stage_ocr(db, doc, extraction)

            # ── Stage 3: Language detection + Cleanup ─────────────────────
            cleaned_text = await _stage_lang_detect_and_cleanup(db, doc, extraction)

            if not cleaned_text.strip():
                logger.warning("No text extracted from document %d", doc.id)
                await _update_job(db, doc.id, "failed", 0, error="No text could be extracted")
                doc.status = DocumentStatus.failed
                await db.commit()
                return

            # ── Stage 4: Chapter splitting ────────────────────────────────
            chapters = await _stage_chapter_split(
                db, doc, cleaned_text, extraction, file_path,
            )

            # ── Done ─────────────────────────────────────────────────────
            doc.status = DocumentStatus.ready
            await _update_job(db, doc.id, "done", 1.0)
            await db.commit()

            logger.info(
                "Document %d ingestion complete: %d chapters",
                doc.id, len(chapters),
            )

        except Exception as exc:
            logger.exception("Ingestion failed for document %d: %s", document_id, exc)
            try:
                doc.status = DocumentStatus.failed
                await _update_job(db, doc.id, "failed", 0, error=str(exc))
                await db.commit()
            except Exception:
                pass
