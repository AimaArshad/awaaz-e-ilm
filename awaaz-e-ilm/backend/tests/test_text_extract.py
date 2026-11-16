"""Tests for the text extraction service (Prompt 2).

Covers:
- PDF extraction with text layer detection (PyMuPDF)
- DOCX extraction (python-docx)
- Image wrapping (PNG / JPG → flagged for OCR)
- File-type dispatcher
- Edge cases: unsupported types, missing files
"""
from __future__ import annotations

import os

import pytest

from app.services.text_extract import (
    ExtractionResult,
    PageResult,
    extract,
    extract_docx,
    extract_image,
    extract_pdf,
    SUPPORTED_EXTENSIONS,
)


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

class TestExtractPDF:
    """Tests for ``extract_pdf`` using PyMuPDF."""

    def test_returns_extraction_result(self, english_pdf_path, tmp_path):
        result = extract_pdf(english_pdf_path, render_dir=str(tmp_path / "pages"))
        assert isinstance(result, ExtractionResult)
        assert result.file_type == "pdf"

    def test_detects_text_layer(self, english_pdf_path, tmp_path):
        """Pages with a text layer should have needs_ocr=False."""
        result = extract_pdf(english_pdf_path, render_dir=str(tmp_path / "pages"))
        assert len(result.pages) >= 1
        for page in result.pages:
            assert page.needs_ocr is False, f"Page {page.page_index} wrongly flagged for OCR"
            assert len(page.text) > 30

    def test_extracts_readable_text(self, english_pdf_path, tmp_path):
        result = extract_pdf(english_pdf_path, render_dir=str(tmp_path / "pages"))
        full = result.full_text.lower()
        assert "chapter 1" in full or "chapter" in full
        assert "quick brown fox" in full or "sample" in full

    def test_page_count(self, english_pdf_path, tmp_path):
        result = extract_pdf(english_pdf_path, render_dir=str(tmp_path / "pages"))
        assert len(result.pages) == 2

    def test_metadata_has_page_count(self, english_pdf_path, tmp_path):
        result = extract_pdf(english_pdf_path, render_dir=str(tmp_path / "pages"))
        assert result.metadata["page_count"] == 2

    def test_scanned_pdf_flagged_for_ocr(self, scanned_pdf_path, tmp_path):
        """A scanned PDF (image-only) should flag pages for OCR."""
        result = extract_pdf(scanned_pdf_path, render_dir=str(tmp_path / "pages"))
        assert len(result.pages) >= 1
        assert any(p.needs_ocr for p in result.pages), \
            "No pages flagged for OCR in scanned PDF"

    def test_scanned_pdf_renders_page_images(self, scanned_pdf_path, tmp_path):
        """Pages flagged for OCR should have a rendered PNG image."""
        render_dir = str(tmp_path / "pages")
        result = extract_pdf(scanned_pdf_path, render_dir=render_dir)
        for page in result.pages_needing_ocr:
            assert page.image_path is not None
            assert os.path.isfile(page.image_path), \
                f"Rendered image not found: {page.image_path}"


# ---------------------------------------------------------------------------
# DOCX extraction
# ---------------------------------------------------------------------------

class TestExtractDOCX:
    """Tests for ``extract_docx`` using python-docx."""

    def test_returns_extraction_result(self, english_docx_path):
        result = extract_docx(english_docx_path)
        assert isinstance(result, ExtractionResult)
        assert result.file_type == "docx"

    def test_extracts_text(self, english_docx_path):
        result = extract_docx(english_docx_path)
        full = result.full_text.lower()
        assert "test" in full or "docx" in full
        assert "chapter" in full or "introduction" in full

    def test_single_page_result(self, english_docx_path):
        """DOCX returns a single PageResult (no pagination concept)."""
        result = extract_docx(english_docx_path)
        assert len(result.pages) == 1
        assert result.pages[0].needs_ocr is False

    def test_paragraph_count_in_metadata(self, english_docx_path):
        result = extract_docx(english_docx_path)
        assert result.metadata["paragraph_count"] > 0


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

class TestExtractImage:
    """Tests for ``extract_image`` — wraps images for downstream OCR."""

    def test_png_flagged_for_ocr(self, english_image_path):
        result = extract_image(english_image_path)
        assert isinstance(result, ExtractionResult)
        assert result.file_type == "image"
        assert len(result.pages) == 1
        assert result.pages[0].needs_ocr is True
        assert result.pages[0].image_path == english_image_path

    def test_jpg_flagged_for_ocr(self, jpg_image_path):
        result = extract_image(jpg_image_path)
        assert result.pages[0].needs_ocr is True


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class TestExtractDispatcher:
    """Tests for the ``extract()`` auto-dispatch function."""

    def test_dispatches_pdf(self, english_pdf_path, tmp_path):
        result = extract(english_pdf_path, render_dir=str(tmp_path))
        assert result.file_type == "pdf"

    def test_dispatches_docx(self, english_docx_path):
        result = extract(english_docx_path)
        assert result.file_type == "docx"

    def test_dispatches_png(self, english_image_path):
        result = extract(english_image_path)
        assert result.file_type == "image"

    def test_unsupported_type_raises(self, tmp_path):
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported"):
            extract(str(bad_file))

    def test_supported_extensions_dict(self):
        """SUPPORTED_EXTENSIONS should include pdf, docx, png, jpg, jpeg."""
        for ext in ("pdf", "docx", "png", "jpg", "jpeg"):
            assert ext in SUPPORTED_EXTENSIONS

