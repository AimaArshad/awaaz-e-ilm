"""Text extraction service.

Extracts text from PDF (via PyMuPDF) and DOCX (via python-docx) files.
For each PDF page, detects whether a text layer exists; pages without
sufficient text are flagged for downstream OCR.

Images (PNG / JPG) are wrapped as single-page results marked for OCR.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Characters-per-page below which we consider the page as "no text layer"
_MIN_TEXT_CHARS = 30


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    """Extraction result for a single logical page / section."""

    page_index: int
    text: str
    needs_ocr: bool = False
    image_path: Optional[str] = None  # path to page image if rendered for OCR


@dataclass
class ExtractionResult:
    """Complete extraction result for one document."""

    pages: List[PageResult] = field(default_factory=list)
    file_type: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenate all page texts."""
        return "\n\n".join(p.text for p in self.pages if p.text)

    @property
    def pages_needing_ocr(self) -> List[PageResult]:
        return [p for p in self.pages if p.needs_ocr]


# ---------------------------------------------------------------------------
# PDF extraction  (PyMuPDF / fitz)
# ---------------------------------------------------------------------------

def extract_pdf(file_path: str, render_dir: Optional[str] = None) -> ExtractionResult:
    """Extract text from a PDF using PyMuPDF.

    For each page:
    - Extract the text layer via ``page.get_text()``.
    - If the text has fewer than ``_MIN_TEXT_CHARS`` characters the page is
      flagged ``needs_ocr=True`` and rendered to a PNG so the OCR service
      can process it later.

    Args:
        file_path: Absolute path to the PDF file.
        render_dir: Directory to write page images into when OCR is needed.
                    If *None* images are written next to the PDF.

    Returns:
        An :class:`ExtractionResult` with one :class:`PageResult` per page.
    """
    import fitz  # PyMuPDF

    if render_dir is None:
        render_dir = os.path.join(os.path.dirname(file_path), "pages")
    os.makedirs(render_dir, exist_ok=True)

    doc = fitz.open(file_path)
    result = ExtractionResult(file_type="pdf", metadata={
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
    })

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text("text") or ""
        text = text.strip()

        needs_ocr = len(text) < _MIN_TEXT_CHARS
        image_path: Optional[str] = None

        if needs_ocr:
            # Render the page to a high-res PNG for OCR
            pix = page.get_pixmap(dpi=300)
            image_path = os.path.join(render_dir, f"page_{page_idx:04d}.png")
            pix.save(image_path)
            logger.info(
                "Page %d has only %d chars — flagged for OCR (%s)",
                page_idx, len(text), image_path,
            )

        result.pages.append(PageResult(
            page_index=page_idx,
            text=text,
            needs_ocr=needs_ocr,
            image_path=image_path,
        ))

    doc.close()
    return result


# ---------------------------------------------------------------------------
# DOCX extraction  (python-docx)
# ---------------------------------------------------------------------------

def extract_docx(file_path: str) -> ExtractionResult:
    """Extract text from a DOCX file using python-docx.

    Reads paragraphs and tables in document order.  Each paragraph is
    emitted on its own line; table cells are separated by tabs.

    Returns:
        An :class:`ExtractionResult` with a *single* :class:`PageResult`
        containing the full document text (DOCX has no fixed page concept).
    """
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)

    parts: list[str] = []
    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            # Paragraph
            para_text = element.text or ""
            # Collect runs for richer extraction
            runs = element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            if runs:
                para_text = "".join(r.text or "" for r in runs)
            if para_text.strip():
                parts.append(para_text)

        elif tag == "tbl":
            # Table — emit each row as tab-separated values
            rows = element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
            for row in rows:
                cells = row.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
                cell_texts = []
                for cell in cells:
                    t_elements = cell.findall(
                        ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                    )
                    cell_texts.append(" ".join(t.text or "" for t in t_elements))
                parts.append("\t".join(cell_texts))

    full_text = "\n".join(parts)

    return ExtractionResult(
        pages=[PageResult(page_index=0, text=full_text)],
        file_type="docx",
        metadata={"paragraph_count": len(parts)},
    )


# ---------------------------------------------------------------------------
# Image files  (PNG / JPG) — always need OCR
# ---------------------------------------------------------------------------

def extract_image(file_path: str) -> ExtractionResult:
    """Wrap an image file as a single-page result flagged for OCR.

    No text extraction is attempted; the downstream OCR service handles it.
    """
    return ExtractionResult(
        pages=[PageResult(
            page_index=0,
            text="",
            needs_ocr=True,
            image_path=file_path,
        )],
        file_type="image",
        metadata={"source": os.path.basename(file_path)},
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

# Supported file extensions mapped to their extractor
SUPPORTED_EXTENSIONS = {
    "pdf": extract_pdf,
    "docx": extract_docx,
    "png": extract_image,
    "jpg": extract_image,
    "jpeg": extract_image,
}


def extract(file_path: str, render_dir: Optional[str] = None) -> ExtractionResult:
    """Auto-detect file type and extract text.

    Args:
        file_path: Path to the uploaded file.
        render_dir: Where to render PDF page images (passed to ``extract_pdf``).

    Returns:
        An :class:`ExtractionResult`.

    Raises:
        ValueError: If the file type is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    extractor = SUPPORTED_EXTENSIONS.get(ext)
    if extractor is None:
        raise ValueError(
            f"Unsupported file type: '.{ext}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if ext == "pdf":
        return extractor(file_path, render_dir=render_dir)
    return extractor(file_path)
