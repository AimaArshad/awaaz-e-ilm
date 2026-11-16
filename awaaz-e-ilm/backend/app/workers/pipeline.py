"""Celery pipeline tasks for document processing.

Task graph (Milestone 2+)
--------------------------
process_document
    ├─ extract_text        (text_extract / ocr)
    ├─ detect_language     (lang_detect)
    ├─ clean_text          (cleanup)
    ├─ split_chapters      (chapters)
    ├─ translate_chapters  (translate) [optional]
    └─ synthesise_audio    (tts/* + audio_stitch)

Each task updates Job.progress and emits a WebSocket event.
"""
from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="pipeline.process_document")
def process_document(self, document_id: int) -> dict:
    """Full document processing pipeline task.

    Args:
        document_id: ID of the Document record to process.

    Returns:
        Dict with final status and chapter count.

    TODO (Milestone 2):
        - Import and call ingestion.ingest_document(document).
        - Use self.update_state() to report progress.
        - Handle retries with self.retry(exc=exc).
    """
    # Stub: just report success
    return {
        "status": "stub_complete",
        "document_id": document_id,
        "message": "Full pipeline coming in Milestone 2.",
    }


@celery_app.task(bind=True, name="pipeline.synthesise_chapter")
def synthesise_chapter(self, chapter_id: int, lang: str = "en") -> dict:
    """TTS synthesis task for a single chapter.

    Args:
        chapter_id: ID of the Chapter record to synthesise.
        lang: Target language code for synthesis.

    Returns:
        Dict with audio_track_id and duration.

    TODO (Milestone 3):
        - Load TTS engine for `lang`.
        - Synthesise chapter text sentence-by-sentence.
        - Stitch clips with audio_stitch.stitch_audio().
        - Save AudioTrack record.
    """
    return {
        "status": "stub_complete",
        "chapter_id": chapter_id,
        "message": "TTS synthesis coming in Milestone 3.",
    }
