"""Tests for the document upload API and ingestion pipeline (Prompts 2 & 3).

Covers:
- POST /documents/ with valid file types (PDF, DOCX, PNG, JPG)
- File-type validation (rejects unsupported types)
- File storage on disk
- Background ingestion pipeline (extraction → OCR → cleanup → chapters)
"""
from __future__ import annotations

import asyncio
import io
import os
import time

import pytest


# ---------------------------------------------------------------------------
# Upload endpoint tests
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    """Tests for POST /documents/ file upload."""

    @pytest.mark.asyncio
    async def test_upload_pdf(self, async_client, english_pdf_path):
        with open(english_pdf_path, "rb") as f:
            content = f.read()
        response = await async_client.post(
            "/documents/",
            files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
            data={"title": "Test PDF"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["file_type"] == "pdf"
        assert data["title"] == "Test PDF"
        assert data["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_upload_docx(self, async_client, english_docx_path):
        with open(english_docx_path, "rb") as f:
            content = f.read()
        response = await async_client.post(
            "/documents/",
            files={"file": ("test.docx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"title": "Test DOCX"},
        )
        assert response.status_code == 201
        assert response.json()["file_type"] == "docx"

    @pytest.mark.asyncio
    async def test_upload_png(self, async_client, english_image_path):
        with open(english_image_path, "rb") as f:
            content = f.read()
        response = await async_client.post(
            "/documents/",
            files={"file": ("test.png", io.BytesIO(content), "image/png")},
            data={"title": "Test Image"},
        )
        assert response.status_code == 201
        assert response.json()["file_type"] == "png"

    @pytest.mark.asyncio
    async def test_upload_jpg(self, async_client, jpg_image_path):
        with open(jpg_image_path, "rb") as f:
            content = f.read()
        response = await async_client.post(
            "/documents/",
            files={"file": ("test.jpg", io.BytesIO(content), "image/jpeg")},
            data={"title": "Test JPG"},
        )
        assert response.status_code == 201
        assert response.json()["file_type"] == "jpg"

    @pytest.mark.asyncio
    async def test_rejects_unsupported_type(self, async_client):
        content = b"not a real document"
        response = await async_client.post(
            "/documents/",
            files={"file": ("test.mp3", io.BytesIO(content), "audio/mpeg")},
            data={"title": "Bad File"},
        )
        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_rejects_txt(self, async_client):
        response = await async_client.post(
            "/documents/",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_title_defaults_to_filename(self, async_client, english_pdf_path):
        with open(english_pdf_path, "rb") as f:
            content = f.read()
        response = await async_client.post(
            "/documents/",
            files={"file": ("mybook.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert response.status_code == 201
        assert response.json()["title"] == "mybook"

    @pytest.mark.asyncio
    async def test_document_appears_in_list(self, async_client, english_pdf_path):
        with open(english_pdf_path, "rb") as f:
            content = f.read()
        upload_resp = await async_client.post(
            "/documents/",
            files={"file": ("listed.pdf", io.BytesIO(content), "application/pdf")},
            data={"title": "Listed Doc"},
        )
        doc_id = upload_resp.json()["id"]

        list_resp = await async_client.get("/documents/")
        assert list_resp.status_code == 200
        ids = [d["id"] for d in list_resp.json()]
        assert doc_id in ids


# ---------------------------------------------------------------------------
# Ingestion pipeline tests (unit-level, synchronous)
# ---------------------------------------------------------------------------

class TestIngestionPipeline:
    """Tests for the ingestion pipeline stages."""

    def test_pdf_extraction_produces_chapters(self, english_pdf_path, tmp_path):
        """Full extraction + chapter split for a text-layer PDF."""
        from app.services.text_extract import extract_pdf
        from app.services.cleanup import clean_text
        from app.services.lang_detect import detect_language
        from app.services.chapters import split_chapters

        result = extract_pdf(english_pdf_path, render_dir=str(tmp_path / "pages"))
        assert len(result.pages) > 0

        full_text = result.full_text
        assert len(full_text) > 50

        lang = detect_language(full_text)
        assert lang == "en"

        cleaned = clean_text(full_text, lang=lang)
        assert len(cleaned) > 0

        chapters = split_chapters(cleaned)
        assert len(chapters) >= 1
        assert all("text" in ch for ch in chapters)
        assert all("title" in ch for ch in chapters)

    def test_docx_extraction_produces_chapters(self, english_docx_path):
        """Full extraction + chapter split for a DOCX file."""
        from app.services.text_extract import extract_docx
        from app.services.cleanup import clean_text
        from app.services.chapters import split_chapters

        result = extract_docx(english_docx_path)
        full_text = result.full_text
        assert len(full_text) > 20

        cleaned = clean_text(full_text, lang="en")
        chapters = split_chapters(cleaned)
        assert len(chapters) >= 1

    def test_image_is_flagged_for_ocr(self, english_image_path):
        """Image files should be wrapped and flagged for OCR."""
        from app.services.text_extract import extract_image

        result = extract_image(english_image_path)
        assert len(result.pages) == 1
        assert result.pages[0].needs_ocr is True
        assert result.pages[0].image_path == english_image_path

