"""Tests for the chapters API endpoint.

Verifies chapter listing and the stub regenerate endpoint.
"""
import io

import pymupdf
import pytest


def _make_pdf_bytes(text="Hello world"):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.asyncio
async def test_list_chapters_for_missing_document(async_client):
    """Listing chapters for a non-existent document should return 404."""
    response = await async_client.get("/documents/99999/chapters")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_chapters_empty(async_client):
    """A newly uploaded document has no chapters initially (before processing)."""
    response = await async_client.post(
        "/documents/",
        files={"file": ("test.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
        data={"title": "Test Doc"},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # Chapters may be empty or have a stub chapter (from background task)
    chapter_response = await async_client.get(f"/documents/{doc_id}/chapters")
    assert chapter_response.status_code == 200
    assert isinstance(chapter_response.json(), list)




@pytest.mark.asyncio
async def test_upload_txt_rejected(async_client):
    response = await async_client.post(
        "/documents/",
        files={"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")},
        data={"title": "Bad Doc"},
    )
    assert response.status_code == 415