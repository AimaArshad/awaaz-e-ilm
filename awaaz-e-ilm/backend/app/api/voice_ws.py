"""WebSocket API endpoints.

/ws/progress/{document_id}
    Streams Job progress updates as JSON messages until the job is done.
    Useful for showing a live progress bar during document processing.

/ws/voice
    Bidirectional WebSocket for push-to-talk voice commands.
    Client sends raw PCM audio frames; server responds with intent JSON.

Milestone notes
---------------
- Milestone 2 wires the progress endpoint to real Celery task events.
- Milestone 4 connects the voice endpoint to the STT + intent pipeline.
"""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db.models import Job
from app.db.session import AsyncSessionLocal

router = APIRouter()


@router.websocket("/ws/progress/{document_id}")
async def ws_progress(websocket: WebSocket, document_id: int):
    """Stream processing progress for a document.

    Sends a JSON message every second:
        {"stage": "...", "progress": 0.0–1.0, "done": false}

    Closes when progress reaches 1.0 or the client disconnects.
    """
    await websocket.accept()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Job)
                    .where(Job.document_id == document_id)
                    .order_by(Job.created_at.desc())
                    .limit(1)
                )
                job = result.scalar_one_or_none()

            if job:
                payload = {
                    "stage": job.stage,
                    "progress": job.progress,
                    "done": job.progress >= 1.0,
                    "error": job.error,
                }
                await websocket.send_text(json.dumps(payload))
                if job.progress >= 1.0:
                    break
            else:
                await websocket.send_text(
                    json.dumps({"stage": "waiting", "progress": 0.0, "done": False})
                )

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    """Push-to-talk voice command endpoint.

    Protocol (Milestone 4):
    1. Client sends binary audio frames (16 kHz, 16-bit mono PCM).
    2. Server accumulates frames until VAD detects end-of-speech.
    3. Server transcribes with Whisper, parses intent, and sends JSON:
           {"transcript": "...", "intent": "...", "params": {...}}

    Current stub: echoes back a placeholder intent so the frontend can
    be built and tested without the full ML pipeline.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                # TODO (Milestone 4): accumulate frames → VAD → Whisper → intent
                stub_response = {
                    "transcript": "(stub — Whisper not yet wired)",
                    "intent": "unknown",
                    "params": {},
                }
                await websocket.send_text(json.dumps(stub_response))
            elif "text" in data:
                # Text frames used for control messages (e.g. {"action": "stop"})
                try:
                    msg = json.loads(data["text"])
                    if msg.get("action") == "stop":
                        break
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
