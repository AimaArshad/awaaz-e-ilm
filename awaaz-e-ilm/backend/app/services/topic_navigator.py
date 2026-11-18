  
# from app.services.topic_navigator import find_topic_in_timing

# T = [
#     {"idx": 0, "start_s": 0.0,  "end_s": 3.0,  "text": "Chapter one. Energy."},
#     {"idx": 1, "start_s": 3.0,  "end_s": 9.0,  "text": "Today we discuss photosynthesis."},
#     {"idx": 2, "start_s": 9.0,  "end_s": 20.0, "text": "Plants use photosynthesis to make food from sunlight and water in the leaves."},
#     {"idx": 3, "start_s": 20.0, "end_s": 28.0, "text": "Kinetic energy is the energy of motion."},
#     {"idx": 4, "start_s": 28.0, "end_s": 40.0, "text": "Newton's second law relates force, mass and acceleration."},
# ]

# def test_exact():
#     assert find_topic_in_timing(T, "photosynthesis")["start_s"] == 3.0   # first strong mention

# def test_split_word_from_whisper():
#     assert find_topic_in_timing(T, "photo synthesis")["idx"] == 1

# def test_multiword():
#     assert find_topic_in_timing(T, "kinetic energy")["idx"] == 3          # NOT the 'Energy.' heading

# def test_apostrophe_and_stopwords():
#     assert find_topic_in_timing(T, "the newtons second law of motion")["idx"] == 4

# def test_not_found():
#     assert find_topic_in_timing(T, "quantum entanglement") is None    
    
"""Find a topic inside a chapter's timing.json (and across chapters)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AudioTrack

logger = logging.getLogger(__name__)

MIN_SCORE = 0.70
MIN_COVERAGE = 0.66
TIE_MARGIN = 0.05
HEADING_BONUS = 0.2
_FUZZY_TOKEN_RATIO = 82

_STOPWORDS = frozenset({
    "a", "an", "the", "of", "on", "about", "regarding", "to", "in", "for", "me",
    "my", "please", "topic", "section", "part", "called", "named", "titled", "is",
    "and", "from", "with", "this", "that", "chapter", "explain", "tell", "read",
    "play", "find", "go", "open", "jump", "show", "start", "take",
})

# Runs of 2+ ALL-CAPS words, e.g. "132 KINETIC THEORY OF GASES" glued into a sentence
_HEADING_RUN = re.compile(r"\b(?:[A-Z]{2,}|A)(?:\s+(?:[A-Z]{2,}|A)){1,9}\b")


def _stem(tok: str) -> str:
    return tok[:-1] if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") else tok


def _tokens(text: str, drop_stop: bool = False) -> list[str]:
    text = (text or "").lower().replace("'", "").replace("’", "")
    out: list[str] = []
    for t in re.findall(r"[^\W_]+", text):
        if len(t) < 2:
            continue
        if drop_stop and t in _STOPWORDS:
            continue
        out.append(_stem(t))
    return out


def _with_joins(tokens: list[str]) -> list[str]:
    """Add adjacent-word joins so 'photo synthesis' can match 'photosynthesis'."""
    return tokens + [a + b for a, b in zip(tokens, tokens[1:])]


def _hit(q: str, pool: list[str]) -> float:
    best = 0.0
    for t in pool:
        if q == t:
            return 1.0
        if len(q) >= 4 and len(t) >= 4 and fuzz.ratio(q, t) >= _FUZZY_TOKEN_RATIO:
            best = 0.9
    return best


def _in_heading(q_tokens: list[str], text: str) -> bool:
    runs = _HEADING_RUN.findall(text)
    if not runs:
        return False
    pool = _with_joins(_tokens(" ".join(runs)))
    coverage = sum(_hit(q, pool) for q in q_tokens) / len(q_tokens)
    return coverage >= MIN_COVERAGE


def _score_sentence(q_tokens: list[str], q_joined: str, q_phrase: str, text: str) -> float:
    s_tokens = _tokens(text)
    if not s_tokens:
        return 0.0
    pool = _with_joins(s_tokens)

    if len(q_tokens) > 1 and _hit(q_joined, pool) > 0:
        coverage = 1.0
    else:
        coverage = sum(_hit(q, pool) for q in q_tokens) / len(q_tokens)
    if coverage < MIN_COVERAGE:
        return 0.0

    phrase = fuzz.partial_ratio(q_phrase, " ".join(s_tokens)) / 100.0
    brevity = min(1.0, 8 / len(s_tokens))
    bonus = HEADING_BONUS if _in_heading(q_tokens, text) else 0.0
    return 0.6 * coverage + 0.3 * phrase + 0.1 * brevity + bonus


def find_topic_in_timing(timing_data: list[dict], query: str,
                         threshold: float = MIN_SCORE) -> dict | None:
    """Return the best timing entry (copy, plus ``score``) or None."""
    q_tokens = _tokens(query, drop_stop=True)
    if not q_tokens or not timing_data:
        return None
    q_joined, q_phrase = "".join(q_tokens), " ".join(q_tokens)

    scored: list[tuple[float, dict]] = []
    for entry in timing_data:
        s = _score_sentence(q_tokens, q_joined, q_phrase, entry.get("text") or "")
        if s > 0:
            scored.append((s, entry))
    if not scored:
        return None

    best = max(s for s, _ in scored)
    if best < threshold:
        return None
    for s, entry in scored:                    # timing is in playback order
        if s >= best - TIE_MARGIN:
            return {**entry, "score": round(s, 3)}
    return None


# ------------------------------------------------------------------ DB helpers
async def get_ready_track(chapter_id: int, lang: str, db: AsyncSession) -> AudioTrack | None:
    result = await db.execute(
        select(AudioTrack)
        .where(
            AudioTrack.chapter_id == chapter_id,
            AudioTrack.lang == lang,
            AudioTrack.status == "ready",
        )
        .order_by(AudioTrack.id.desc())
        .limit(1)
    )
    return result.scalars().first()


def load_timing(track: AudioTrack) -> list[dict] | None:
    if not track.timing_path:
        return None
    path = Path(track.timing_path)
    if not path.exists():
        logger.warning("Timing file missing: %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed reading timing %s: %s", path, exc)
        return None


async def get_timing_data(chapter_id: int, lang: str, db: AsyncSession) -> list[dict] | None:
    track = await get_ready_track(chapter_id, lang, db)
    return load_timing(track) if track else None 
    