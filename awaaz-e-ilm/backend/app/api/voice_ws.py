# """WebSocket API endpoints: /ws/progress/{document_id} and /ws/voice."""
# import asyncio
# import json
# import logging

# from fastapi import APIRouter, WebSocket, WebSocketDisconnect
# from sqlalchemy import select

# from app.config import get_settings
# from app.db.models import Job
# from app.db.session import AsyncSessionLocal
# from app.services.command_orchestrator import handle_navigate_topic
# from app.services.intent.parser import parse_intent
# from app.services.stt import transcribe

# logger = logging.getLogger(__name__)
# router = APIRouter()

# MAX_UTTERANCE_BYTES = 16000 * 2 * 30  # 30 s of 16 kHz int16 mono


# @router.websocket("/ws/progress/{document_id}")
# async def ws_progress(websocket: WebSocket, document_id: int):
#     await websocket.accept()
#     try:
#         while True:
#             async with AsyncSessionLocal() as db:
#                 result = await db.execute(
#                     select(Job).where(Job.document_id == document_id)
#                     .order_by(Job.created_at.desc()).limit(1)
#                 )
#                 job = result.scalar_one_or_none()
#             if job:
#                 await websocket.send_text(json.dumps({
#                     "stage": job.stage, "progress": job.progress,
#                     "done": job.progress >= 1.0, "error": job.error,
#                 }))
#                 if job.progress >= 1.0:
#                     break
#             else:
#                 await websocket.send_text(
#                     json.dumps({"stage": "waiting", "progress": 0.0, "done": False}))
#             await asyncio.sleep(1)
#     except WebSocketDisconnect:
#         pass
#     finally:
#         try:
#             await websocket.close()
#         except Exception:
#             pass


# async def _process_utterance(websocket: WebSocket, pcm: bytes, chapter_id: int | None) -> None:
#     settings = get_settings()
#     try:
#         stt = await transcribe(pcm, lang=settings.stt_language or None)
#     except Exception:
#         logger.exception("STT failed")
#         await websocket.send_json({"action": "error",
#                                    "message": "Sorry, I couldn't process that audio."})
#         return

#     transcript = stt["text"].strip()
#     if not transcript:
#         await websocket.send_json({"action": "no_speech",
#                                    "message": "I didn't catch that. Please try again."})
#         return

#     parsed = parse_intent(transcript)
#     intent, params = parsed["intent"], parsed["params"]
#     logger.info("voice: '%s' -> intent=%s params=%s", transcript, intent, params)

#     if intent == "navigate_topic":
#         async with AsyncSessionLocal() as db:
#             await handle_navigate_topic(websocket, params, chapter_id, db)
#     elif intent == "help":
#         await websocket.send_json({
#             "action": "help",
#             "message": "You can say: play the topic on photosynthesis, "
#                        "or forward thirty seconds.",
#         })
#     else:
#         await websocket.send_json({
#             "action": "unknown",
#             "message": f"Sorry, I didn't understand {transcript}.",
#         })


# @router.websocket("/ws/voice")
# async def ws_voice(websocket: WebSocket):
#     """Protocol: optional {"action":"set_chapter","chapter_id":N}; binary 16 kHz int16 mono
#     PCM frames; {"action":"end_speech"} to transcribe and act."""
#     await websocket.accept()
#     current_chapter_id: int | None = None
#     audio_buffer = bytearray()

#     try:
#         while True:
#             data = await websocket.receive()
#             if data.get("type") == "websocket.disconnect":
#                 break

#             if data.get("bytes") is not None:
#                 if len(audio_buffer) < MAX_UTTERANCE_BYTES:
#                     audio_buffer.extend(data["bytes"])
#                 continue

#             if data.get("text") is None:
#                 continue
#             try:
#                 msg = json.loads(data["text"])
#             except json.JSONDecodeError:
#                 continue

#             action = msg.get("action")
#             if action == "set_chapter":
#                 current_chapter_id = msg.get("chapter_id")
#                 audio_buffer.clear()
#                 logger.info("voice: current chapter = %s", current_chapter_id)

#             elif action == "end_speech":
#                 if not audio_buffer:
#                     await websocket.send_json(
#                         {"action": "no_speech", "message": "I didn't hear anything."})
#                     continue
#                 pcm = bytes(audio_buffer)
#                 audio_buffer.clear()
#                 try:
#                     await _process_utterance(websocket, pcm, current_chapter_id)
#                 except WebSocketDisconnect:
#                     raise
#                 except Exception:
#                     logger.exception("voice: command failed")
#                     await websocket.send_json(
#                         {"action": "error", "message": "Something went wrong. Please try again."})

#             elif action == "stop":
#                 break
#     except WebSocketDisconnect:
#         logger.info("voice: client disconnected")
#     except Exception:
#         logger.exception("voice: unexpected error")
#     finally:
#         try:
#             await websocket.close()
#         except Exception:
#             pass



"""WebSocket API endpoints: /ws/progress/{document_id} and /ws/voice."""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Job
from app.db.session import AsyncSessionLocal
from app.services.command_orchestrator import VoiceSession, dispatch_command, log_command
from app.services.intent.parser import parse_intent
from app.services.stt import transcribe

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UTTERANCE_BYTES = 16000 * 2 * 30  # 30 s of 16 kHz int16 mono


@router.websocket("/ws/progress/{document_id}")
async def ws_progress(websocket: WebSocket, document_id: int):
    await websocket.accept()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Job).where(Job.document_id == document_id)
                    .order_by(Job.created_at.desc()).limit(1)
                )
                job = result.scalar_one_or_none()
            if job:
                await websocket.send_text(json.dumps({
                    "stage": job.stage, "progress": job.progress,
                    "done": job.progress >= 1.0, "error": job.error,
                }))
                if job.progress >= 1.0:
                    break
            else:
                await websocket.send_text(
                    json.dumps({"stage": "waiting", "progress": 0.0, "done": False}))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def _process_utterance(session: VoiceSession, pcm: bytes) -> None:
    settings = get_settings()
    try:
        stt = await transcribe(pcm, lang=settings.stt_language or None)
    except Exception:
        logger.exception("STT failed")
        await session.send({"action": "error", "message": "Sorry, I couldn't process that audio."})
        return

    transcript = stt["text"].strip()
    if not transcript:
        await session.send({"action": "no_speech", "message": "I didn't catch that. Please try again."})
        return

    parsed = parse_intent(transcript)
    logger.info("voice: '%s' -> intent=%s params=%s", transcript, parsed["intent"], parsed["params"])

    async with AsyncSessionLocal() as db:
        ok = await dispatch_command(session, parsed, transcript, db)
        await log_command(db, transcript, parsed["intent"], parsed["params"], ok)


@router.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    """Protocol: optional {"action":"set_chapter","chapter_id":N}; binary 16 kHz int16 mono
    PCM frames; {"action":"end_speech"} to transcribe and act."""
    await websocket.accept()
    session = VoiceSession(websocket)
    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break

            if data.get("bytes") is not None:
                if len(audio_buffer) < MAX_UTTERANCE_BYTES:
                    audio_buffer.extend(data["bytes"])
                continue
            if data.get("text") is None:
                continue
            try:
                msg = json.loads(data["text"])
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            if action == "set_chapter":
                session.current_chapter_id = msg.get("chapter_id")
                audio_buffer.clear()

            elif action == "end_speech":
                if not audio_buffer:
                    await session.send({"action": "no_speech", "message": "I didn't hear anything."})
                    continue
                pcm = bytes(audio_buffer)
                audio_buffer.clear()
                try:
                    await _process_utterance(session, pcm)
                except WebSocketDisconnect:
                    raise
                except Exception:
                    logger.exception("voice: command failed")
                    await session.send({"action": "error",
                                        "message": "Something went wrong. Please try again."})

            elif action == "stop":
                break
    except WebSocketDisconnect:
        logger.info("voice: client disconnected")
    except Exception:
        logger.exception("voice: unexpected error")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass