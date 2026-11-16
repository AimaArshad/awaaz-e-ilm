"""Generate test fixture files for backend tests.

Creates sample PDF, DOCX, PNG, and JPG files in the test fixtures directory.
Run once: ``python -m scripts.generate_fixtures`` or ``pytest`` uses them via conftest.

These are minimal files designed for fast CI — not for testing real-world OCR quality.
"""
from __future__ import annotations

import os
import sys

# Resolve paths
FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend", "tests", "fixtures",
)


def generate_english_pdf(output_path: str) -> str:
    """Create a simple 2-page English PDF with a text layer via PyMuPDF."""
    import fitz

    doc = fitz.open()

    # Page 1
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text(
        (72, 100),
        "Chapter 1\n\nThis is a sample English document for testing the text "
        "extraction pipeline. It contains multiple paragraphs of text that "
        "should be extractable without OCR.\n\n"
        "The quick brown fox jumps over the lazy dog. This sentence contains "
        "every letter of the English alphabet.",
        fontsize=12,
    )

    # Page 2
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text(
        (72, 100),
        "Chapter 2\n\nThis is the second chapter of the sample document. "
        "It tests chapter detection and multi-page extraction.\n\n"
        "Mathematics and science are fundamental to human progress. "
        "Education is the key to a better future.",
        fontsize=12,
    )

    doc.save(output_path)
    doc.close()
    return output_path


def generate_scanned_pdf(output_path: str) -> str:
    """Create a PDF with an embedded image (no text layer) — simulates a scanned page."""
    import fitz
    from PIL import Image, ImageDraw, ImageFont

    # Create an image with text rendered on it
    img = Image.new("RGB", (612, 792), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()

    lines = [
        "This is a scanned page.",
        "The text here is part of an image,",
        "so there is no text layer in the PDF.",
        "OCR must be used to extract this text.",
    ]
    y = 100
    for line in lines:
        draw.text((72, y), line, fill="black", font=font)
        y += 30

    img_path = output_path.replace(".pdf", "_page.png")
    img.save(img_path)

    # Build a PDF with only the image (no text layer)
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    rect = fitz.Rect(0, 0, 612, 792)
    page.insert_image(rect, filename=img_path)
    doc.save(output_path)
    doc.close()

    # Clean up temp image
    if os.path.isfile(img_path):
        os.remove(img_path)

    return output_path


def generate_english_docx(output_path: str) -> str:
    """Create a simple DOCX with English paragraphs."""
    from docx import Document

    doc = Document()
    doc.add_heading("Chapter 1: Introduction", level=1)
    doc.add_paragraph(
        "This is a test DOCX document. It contains multiple paragraphs "
        "for testing the python-docx extraction service."
    )
    doc.add_paragraph(
        "The second paragraph provides additional content for chapter "
        "detection and language identification."
    )
    doc.add_heading("Chapter 2: Methods", level=1)
    doc.add_paragraph(
        "This chapter covers the methodology used in this study. "
        "Various techniques were employed to gather data."
    )
    doc.save(output_path)
    return output_path


def generate_english_image(output_path: str) -> str:
    """Create a PNG image with English text for OCR testing."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text((40, 40), "The quick brown fox jumps over the lazy dog.", fill="black", font=font)
    draw.text((40, 100), "This text should be recognizable by OCR engines.", fill="black", font=font)
    img.save(output_path)
    return output_path


def generate_urdu_image(output_path: str) -> str:
    """Create a PNG image with Urdu text for OCR testing.

    Note: Rendering Nastaliq properly requires an appropriate font.
    This creates a best-effort image; actual OCR accuracy on this
    image will vary.
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)

    # Try to use a Nastaliq font if available
    font = None
    for font_name in ["Jameel Noori Nastaleeq.ttf", "NotoNastaliqUrdu-Regular.ttf", "arial.ttf"]:
        try:
            font = ImageFont.truetype(font_name, 28)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    # Urdu text — "This is a test of the Urdu language."
    urdu_text = "یہ اردو زبان کا ایک ٹیسٹ ہے۔"
    draw.text((40, 40), urdu_text, fill="black", font=font)
    img.save(output_path)
    return output_path


def generate_all() -> dict[str, str]:
    """Generate all fixture files.  Returns a dict of name → path."""
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    fixtures = {}

    try:
        fixtures["english_pdf"] = generate_english_pdf(
            os.path.join(FIXTURES_DIR, "sample_english.pdf")
        )
    except Exception as e:
        print(f"⚠  Could not generate english PDF: {e}")

    try:
        fixtures["scanned_pdf"] = generate_scanned_pdf(
            os.path.join(FIXTURES_DIR, "sample_scanned.pdf")
        )
    except Exception as e:
        print(f"⚠  Could not generate scanned PDF: {e}")

    try:
        fixtures["english_docx"] = generate_english_docx(
            os.path.join(FIXTURES_DIR, "sample_english.docx")
        )
    except Exception as e:
        print(f"⚠  Could not generate english DOCX: {e}")

    try:
        fixtures["english_image"] = generate_english_image(
            os.path.join(FIXTURES_DIR, "sample_english.png")
        )
    except Exception as e:
        print(f"⚠  Could not generate english image: {e}")

    try:
        fixtures["urdu_image"] = generate_urdu_image(
            os.path.join(FIXTURES_DIR, "sample_urdu.png")
        )
    except Exception as e:
        print(f"⚠  Could not generate urdu image: {e}")

    # Also create ground-truth files for accuracy testing
    gt_dir = os.path.join(FIXTURES_DIR, "ground_truth")
    os.makedirs(gt_dir, exist_ok=True)

    with open(os.path.join(gt_dir, "english_image.txt"), "w", encoding="utf-8") as f:
        f.write(
            "The quick brown fox jumps over the lazy dog.\n"
            "This text should be recognizable by OCR engines.\n"
        )
    fixtures["english_image_gt"] = os.path.join(gt_dir, "english_image.txt")

    with open(os.path.join(gt_dir, "urdu_image.txt"), "w", encoding="utf-8") as f:
        f.write("یہ اردو زبان کا ایک ٹیسٹ ہے۔\n")
    fixtures["urdu_image_gt"] = os.path.join(gt_dir, "urdu_image.txt")

    return fixtures


if __name__ == "__main__":
    result = generate_all()
    for name, path in result.items():
        print(f"  ✓ {name}: {path}")
    print(f"\nGenerated {len(result)} fixtures in {FIXTURES_DIR}")

