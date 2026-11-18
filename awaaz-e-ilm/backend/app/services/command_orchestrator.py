# # # """Handles complex voice commands that need DB lookups.

# # # Feature 1 (this file at this stage): topic navigation.
# # # Feature 2 will add open_book_chapter and other handlers here.
# # # """
# # # from __future__ import annotations

# # # import logging

# # # from fastapi import WebSocket
# # # from sqlalchemy.ext.asyncio import AsyncSession

# # # from app.services.topic_navigator import (
# # #     find_topic_in_timing,
# # #     get_timing_data,
# # # )

# # # logger = logging.getLogger(__name__)


# # # async def handle_navigate_topic(
# # #     websocket: WebSocket,
# # #     params: dict,
# # #     current_chapter_id: int | None,
# # #     db: AsyncSession,
# # # ) -> None:
# # #     """Seek to a topic inside the current chapter and start playing."""
# # #     query = (params.get("topic") or "").strip()
# # #     if not query:
# # #         await websocket.send_json(
# # #             {"action": "error", "message": "Which topic did you mean?"}
# # #         )
# # #         return

# # #     if current_chapter_id is None:
# # #         await websocket.send_json(
# # #             {"action": "error",
# # #              "message": "Please open a chapter first before asking for a topic."}
# # #         )
# # #         return

# # #     # Try English first; if no result and the chapter has Urdu audio, try Urdu
# # #     timing = await get_timing_data(current_chapter_id, "en", db)
# # #     lang_used = "en"
# # #     if not timing:
# # #         timing = await get_timing_data(current_chapter_id, "ur", db)
# # #         lang_used = "ur"

# # #     if not timing:
# # #         await websocket.send_json(
# # #             {"action": "error",
# # #              "message": "Audio for this chapter isn't ready yet."}
# # #         )
# # #         return

# # #     match = find_topic_in_timing(timing, query)
# # #     if not match:
# # #         await websocket.send_json(
# # #             {"action": "not_found",
# # #              "message": f"I couldn't find a section about '{query}' in this chapter."}
# # #         )
# # #         return

# # #     await websocket.send_json({
# # #         "action": "seek_and_play",
# # #         "time": float(match["start_s"]),
# # #         "text": match["text"],
# # #         "lang": lang_used,
# # #         "message": f"Playing: {match['text'][:80]}",
# # #     })




# # """Handles complex voice commands that need DB lookups.

# # Feature 1: topic navigation (current chapter first, then other ready chapters
# # of the same document). Feature 2 will add open_chapter handlers here.
# # """
# # from __future__ import annotations

# # import logging

# # from fastapi import WebSocket
# # from sqlalchemy import select
# # from sqlalchemy.ext.asyncio import AsyncSession

# # from app.db.models import Chapter
# # from app.services.topic_navigator import (
# #     find_topic_in_timing,
# #     get_ready_track,
# #     load_timing,
# # )

# # logger = logging.getLogger(__name__)
# # _LANGS = ("en", "ur")


# # async def _search_chapter(chapter: Chapter, query: str, db: AsyncSession):
# #     """Return (hit_or_None, had_ready_audio, was_truncated)."""
# #     had_audio, truncated = False, False
# #     for lang in _LANGS:
# #         track = await get_ready_track(chapter.id, lang, db)
# #         if not track:
# #             continue
# #         timing = load_timing(track)
# #         if not timing:
# #             continue
# #         had_audio = True
# #         truncated = truncated or bool(track.truncated)
# #         entry = find_topic_in_timing(timing, query)
# #         if entry:
# #             return {"chapter": chapter, "lang": lang, "entry": entry}, True, truncated
# #     return None, had_audio, truncated


# # async def handle_navigate_topic(
# #     websocket: WebSocket,
# #     params: dict,
# #     current_chapter_id: int | None,
# #     db: AsyncSession,
# # ) -> None:
# #     query = (params.get("topic") or "").strip()
# #     if not query:
# #         await websocket.send_json({"action": "error", "message": "Which topic did you mean?"})
# #         return
# #     if current_chapter_id is None:
# #         await websocket.send_json({
# #             "action": "error",
# #             "message": "Please open a chapter first, then ask for a topic.",
# #         })
# #         return

# #     current = await db.get(Chapter, current_chapter_id)
# #     if current is None:
# #         await websocket.send_json({"action": "error", "message": "I lost track of the chapter."})
# #         return

# #     # 1) current chapter
# #     hit, cur_audio, cur_trunc = await _search_chapter(current, query, db)
# #     any_audio, any_trunc, total_other, ready_other = cur_audio, cur_trunc, 0, 0

# #     # 2) other chapters of the same document
# #     if hit is None:
# #         result = await db.execute(
# #             select(Chapter)
# #             .where(Chapter.document_id == current.document_id, Chapter.id != current.id)
# #             .order_by(Chapter.index)
# #         )
# #         best = None
# #         for ch in result.scalars():
# #             total_other += 1
# #             h, had_audio, trunc = await _search_chapter(ch, query, db)
# #             ready_other += int(had_audio)
# #             any_audio = any_audio or had_audio
# #             any_trunc = any_trunc or trunc
# #             if h and (best is None or h["entry"]["score"] > best["entry"]["score"]):
# #                 best = h
# #         hit = best

# #     if hit is None:
# #         if not any_audio:
# #             msg = "Audio for this chapter isn't ready yet."
# #         else:
# #             msg = f"I couldn't find a section about {query}."
# #             if any_trunc:
# #                 msg += " Some audio was shortened, so it may be past the end."
# #             if total_other and ready_other < total_other:
# #                 msg += " Some chapters are not prepared yet, so it may be in one of those."
# #         await websocket.send_json({"action": "not_found", "message": msg})
# #         return

# #     ch, entry = hit["chapter"], hit["entry"]
# #     if ch.id == current.id:
# #         message = f"Playing the section on {query}."
# #     else:
# #         message = f"Found {query} in chapter {ch.index + 1}. Playing it now."

# #     logger.info("topic '%s' -> chapter %s @ %.2fs (score %.2f)",
# #                 query, ch.id, float(entry["start_s"]), entry["score"])
# #     await websocket.send_json({
# #         "action": "seek_and_play",
# #         "chapter_id": ch.id,
# #         "chapter_index": ch.index,
# #         "time": float(entry["start_s"]),
# #         "text": entry["text"],
# #         "lang": hit["lang"],
# #         "score": entry["score"],
# #         "message": message,
# #     })


# """Handles complex voice commands that need DB lookups (Feature 1: topic navigation)."""
# from __future__ import annotations

# import logging

# from fastapi import WebSocket
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.models import Chapter
# from app.services.topic_navigator import (
#     find_topic_in_timing,
#     get_ready_track,
#     load_timing,
# )

# logger = logging.getLogger(__name__)
# _LANGS = ("en", "ur")


# async def _search_chapter(chapter: Chapter, query: str, db: AsyncSession):
#     """Return (hit_or_None, had_ready_audio, was_truncated)."""
#     had_audio, truncated = False, False
#     for lang in _LANGS:
#         track = await get_ready_track(chapter.id, lang, db)
#         if not track:
#             continue
#         timing = load_timing(track)
#         if not timing:
#             continue
#         had_audio = True
#         truncated = truncated or bool(track.truncated)
#         entry = find_topic_in_timing(timing, query)
#         if entry:
#             return {"chapter": chapter, "lang": lang, "entry": entry}, True, truncated
#     return None, had_audio, truncated


# async def handle_navigate_topic(
#     websocket: WebSocket,
#     params: dict,
#     current_chapter_id: int | None,
#     db: AsyncSession,
# ) -> None:
#     query = (params.get("topic") or "").strip()
#     if not query:
#         await websocket.send_json({"action": "error", "message": "Which topic did you mean?"})
#         return
#     if current_chapter_id is None:
#         await websocket.send_json({
#             "action": "error",
#             "message": "Please open a chapter first, then ask for a topic.",
#         })
#         return

#     current = await db.get(Chapter, current_chapter_id)
#     if current is None:
#         await websocket.send_json({"action": "error", "message": "I lost track of the chapter."})
#         return

#     hit, cur_audio, cur_trunc = await _search_chapter(current, query, db)
#     any_audio, any_trunc, total_other, ready_other = cur_audio, cur_trunc, 0, 0

#     if hit is None:
#         result = await db.execute(
#             select(Chapter)
#             .where(Chapter.document_id == current.document_id, Chapter.id != current.id)
#             .order_by(Chapter.index)
#         )
#         best = None
#         for ch in result.scalars():
#             total_other += 1
#             h, had_audio, trunc = await _search_chapter(ch, query, db)
#             ready_other += int(had_audio)
#             any_audio = any_audio or had_audio
#             any_trunc = any_trunc or trunc
#             if h and (best is None or h["entry"]["score"] > best["entry"]["score"]):
#                 best = h
#         hit = best

#     if hit is None:
#         if not any_audio:
#             msg = "Audio for this chapter isn't ready yet."
#         else:
#             msg = f"I couldn't find a section about {query}."
#             if any_trunc:
#                 msg += " Some audio was shortened, so it may be past the end."
#             if total_other and ready_other < total_other:
#                 msg += " Some chapters are not prepared yet, so it may be in one of those."
#         await websocket.send_json({"action": "not_found", "message": msg})
#         return

#     ch, entry = hit["chapter"], hit["entry"]
#     message = (f"Playing the section on {query}." if ch.id == current.id
#                else f"Found {query} in chapter {ch.index + 1}. Playing it now.")
#     logger.info("topic '%s' -> chapter %s @ %.2fs (score %.2f)",
#                 query, ch.id, float(entry["start_s"]), entry["score"])
#     await websocket.send_json({
#         "action": "seek_and_play",
#         "chapter_id": ch.id,
#         "chapter_index": ch.index,
#         "time": float(entry["start_s"]),
#         "text": entry["text"],
#         "lang": hit["lang"],
#         "score": entry["score"],
#         "message": message,
#     })

"""Voice command handlers that need the DB (topic search, open chapter) plus a
dispatcher for every intent. Each handler returns True on success.

WebSocket messages sent to the browser:
  seek_and_play        {chapter_id, time, message}                     (topic found)
  play_chapter         {document_id, chapter_id, message}              (audio cached)
  generating           {document_id, chapter_id, message}              (generation started)
  generation_complete  {document_id, document_title, chapter_id, chapter_number, message}
  generation_failed    {message}
  play / pause / seek_relative / set_speed / repeat_sentence / next_chapter / prev_chapter
  help / info / not_found / unknown / error
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketState

from app.db.models import Chapter, CommandLog, Document, User
from app.db.session import AsyncSessionLocal
from app.services.audio_jobs import ensure_audio, get_track, spawn
from app.services.library_resolver import (
    describe_range, list_titles, pick_chapter, resolve_document,
)
from app.services.topic_navigator import find_topic_in_timing, get_ready_track, load_timing

logger = logging.getLogger(__name__)

AUDIO_LANG = "en"           # TODO: per-chapter language once Urdu TTS exists
_LANGS = ("en", "ur")
GENERATION_TIMEOUT_S = 3600

HELP_MESSAGE = (
    "You can say: open chapter five, physics first year. "
    "Play the topic on photosynthesis. Forward thirty seconds. Back thirty seconds. "
    "Next chapter. Previous chapter. Pause. Play. Faster. Slower. Repeat."
)


class VoiceSession:
    """State of one /ws/voice connection."""

    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.current_chapter_id: int | None = None
        self.watching: set[int] = set()

    def closed(self) -> bool:
        return self.ws.client_state != WebSocketState.CONNECTED

    async def send(self, payload: dict) -> bool:
        if self.closed():
            return False
        try:
            await self.ws.send_json(payload)
            return True
        except Exception:
            return False


def _label(ch: Chapter, n: int) -> str:
    title = (ch.title or "").strip()
    if re.match(r"(?i)\s*(chapter|unit|section)\b", title):
        return title
    return f"chapter {n}, {title}" if title else f"chapter {n}"


# ============================================================ topic navigation
async def _search_chapter(chapter: Chapter, query: str, db: AsyncSession):
    had_audio, truncated = False, False
    for lang in _LANGS:
        track = await get_ready_track(chapter.id, lang, db)
        if not track:
            continue
        timing = load_timing(track)
        if not timing:
            continue
        had_audio = True
        truncated = truncated or bool(track.truncated)
        entry = find_topic_in_timing(timing, query)
        if entry:
            return {"chapter": chapter, "lang": lang, "entry": entry}, True, truncated
    return None, had_audio, truncated


async def handle_navigate_topic(session: VoiceSession, params: dict, db: AsyncSession) -> bool:
    query = (params.get("topic") or "").strip()
    if not query:
        await session.send({"action": "error", "message": "Which topic did you mean?"})
        return False
    if session.current_chapter_id is None:
        await session.send({"action": "error",
                            "message": "Please open a chapter first, then ask for a topic."})
        return False
    current = await db.get(Chapter, session.current_chapter_id)
    if current is None:
        await session.send({"action": "error", "message": "I lost track of the chapter."})
        return False

    hit, cur_audio, cur_trunc = await _search_chapter(current, query, db)
    any_audio, any_trunc, total_other, ready_other = cur_audio, cur_trunc, 0, 0

    if hit is None:
        result = await db.execute(
            select(Chapter)
            .where(Chapter.document_id == current.document_id, Chapter.id != current.id)
            .order_by(Chapter.index)
        )
        best = None
        for ch in result.scalars():
            total_other += 1
            h, had_audio, trunc = await _search_chapter(ch, query, db)
            ready_other += int(had_audio)
            any_audio = any_audio or had_audio
            any_trunc = any_trunc or trunc
            if h and (best is None or h["entry"]["score"] > best["entry"]["score"]):
                best = h
        hit = best

    if hit is None:
        if not any_audio:
            msg = "Audio for this chapter isn't ready yet."
        else:
            msg = f"I couldn't find a section about {query}."
            if any_trunc:
                msg += " Some audio was shortened, so it may be past the end."
            if total_other and ready_other < total_other:
                msg += " Some chapters are not prepared yet, so it may be in one of those."
        await session.send({"action": "not_found", "message": msg})
        return False

    ch, entry = hit["chapter"], hit["entry"]
    message = (f"Playing the section on {query}." if ch.id == current.id
               else f"Found {query} in chapter {ch.index + 1}. Playing it now.")
    await session.send({
        "action": "seek_and_play", "chapter_id": ch.id, "chapter_index": ch.index,
        "time": float(entry["start_s"]), "text": entry["text"], "lang": hit["lang"],
        "score": entry["score"], "message": message,
    })
    return True


# ================================================================ open chapter
async def _watch_generation(session: VoiceSession, base: dict, label: str) -> None:
    chapter_id, lang = base["chapter_id"], base["lang"]
    try:
        waited = 0.0
        while waited < GENERATION_TIMEOUT_S:
            await asyncio.sleep(2.0)
            waited += 2.0
            if session.closed():
                return
            async with AsyncSessionLocal() as db:
                track = await get_track(chapter_id, lang, db)
            if track is None or track.status == "failed":
                await session.send({
                    "action": "generation_failed", **base,
                    "message": f"Sorry, I couldn't prepare {label}. Please try again.",
                })
                return
            if track.status == "ready":
                await session.send({
                    "action": "generation_complete", **base,
                    "message": f"Audio generation for {label} is complete.",
                })
                return
        await session.send({"action": "generation_failed", **base,
                            "message": f"Preparing {label} is taking too long. Please try again later."})
    finally:
        session.watching.discard(chapter_id)


async def handle_open_chapter(session: VoiceSession, params: dict, db: AsyncSession) -> bool:
    n = params["chapter"]
    query = params.get("book")

    if query:
        doc, ambiguous = await resolve_document(query, db)
        if doc is None:
            if ambiguous:
                names = ", ".join(d.title for d in ambiguous[:4])
                msg = f"I found more than one book for {query}: {names}. Please say the full name."
            else:
                msg = f"I couldn't find a book called {query}."
                titles = await list_titles(db)
                if titles:
                    msg += " Your books are: " + ", ".join(titles[:5]) + "."
            await session.send({"action": "error", "message": msg})
            return False
    else:
        cur = await db.get(Chapter, session.current_chapter_id) if session.current_chapter_id else None
        if cur is None:
            await session.send({"action": "error",
                                "message": "Which book? Say, for example, open chapter five, physics first year."})
            return False
        doc = await db.get(Document, cur.document_id)

    chapters = (await db.execute(
        select(Chapter).where(Chapter.document_id == doc.id).order_by(Chapter.index)
    )).scalars().all()
    ch = pick_chapter(chapters, n)
    if ch is None:
        await session.send({"action": "error",
                            "message": f"I couldn't find chapter {n} in {doc.title}. {describe_range(chapters)}"})
        return False

    label = _label(ch, n)
    state = await ensure_audio(ch.id, AUDIO_LANG, db)
    base = {
        "document_id": doc.id, "document_title": doc.title, "chapter_id": ch.id,
        "chapter_index": ch.index, "chapter_number": n, "title": ch.title, "lang": AUDIO_LANG,
    }

    if state == "ready":
        msg = f"Opening {label}." + (f" From {doc.title}." if query else "")
        await session.send({"action": "play_chapter", **base, "message": msg})
        return True

    verb = "is still being prepared" if state == "processing" else "isn't ready yet. I'm preparing it now"
    await session.send({"action": "generating", **base,
                        "message": f"{label} {verb}. I'll tell you when it's done."})
    if ch.id not in session.watching:
        session.watching.add(ch.id)
        spawn(_watch_generation(session, base, label))
    return True


# ================================================================== dispatcher
def _simple_command(intent: str, params: dict, transcript: str) -> dict | None:
    if intent == "play":
        return {"action": "play", "message": "Playing."}
    if intent == "pause":
        return {"action": "pause", "message": "Paused."}
    if intent in ("seek_forward", "seek_backward"):
        s = int(params.get("seconds", 30))
        if intent == "seek_backward":
            return {"action": "seek_relative", "seconds": -s, "message": f"Back {s} seconds."}
        return {"action": "seek_relative", "seconds": s, "message": f"Forward {s} seconds."}
    if intent == "next_chapter":
        return {"action": "next_chapter"}
    if intent == "prev_chapter":
        return {"action": "prev_chapter"}
    if intent == "repeat":
        return {"action": "repeat_sentence", "message": "Repeating."}
    if intent == "help":
        return {"action": "help", "message": HELP_MESSAGE}
    if intent == "set_speed":
        if "speed" in params:
            return {"action": "set_speed", "speed": params["speed"]}
        if "relative" in params:
            return {"action": "set_speed", "relative": params["relative"]}
        return {"action": "error", "message": "Say a speed, like speed one point five, or say faster or slower."}
    if intent == "set_language":
        if params.get("lang") == "ur":
            return {"action": "error", "message": "Urdu audio isn't available yet."}
        return {"action": "info", "message": "I'm already reading in English."}
    return None


async def dispatch_command(session: VoiceSession, parsed: dict, transcript: str, db: AsyncSession) -> bool:
    intent, params = parsed["intent"], parsed["params"]

    if intent == "navigate_topic":
        return await handle_navigate_topic(session, params, db)
    if intent == "open_chapter":
        return await handle_open_chapter(session, params, db)

    msg = _simple_command(intent, params, transcript)
    if msg is None:
        await session.send({"action": "unknown",
                            "message": f"Sorry, I didn't understand {transcript}. Say help for commands."})
        return False
    await session.send(msg)
    return msg["action"] != "error"


async def log_command(db: AsyncSession, transcript: str, intent: str, params: dict, success: bool) -> None:
    """Write a command_log row. Never lets logging break the command."""
    try:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if user is None:
            return
        db.add(CommandLog(user_id=user.id, transcript=transcript, intent=intent,
                          params=json.dumps(params, ensure_ascii=False), success=success))
        await db.commit()
    except Exception:
        logger.exception("command_log write failed")
        await db.rollback()
