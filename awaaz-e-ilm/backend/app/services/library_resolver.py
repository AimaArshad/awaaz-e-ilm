"""Resolve "physics first year" -> a Document, and "chapter 5" -> a Chapter.

Pure helpers (canon_tokens, score_title, title_number, pick_chapter) are unit-tested
without a database.
"""
from __future__ import annotations

import re
from typing import Sequence

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentStatus

MIN_DOC_SCORE = 0.6
_AMBIGUITY_MARGIN = 0.03

# "first year" == "1st year" == class 11 (Punjab board); "second year" == class 12
_CANON: dict[str, str] = {}
for _w in ("first", "1st", "1", "one", "11", "11th", "eleventh", "xi"):
    _CANON[_w] = "y1"
for _w in ("second", "2nd", "2", "two", "12", "12th", "twelfth", "xii"):
    _CANON[_w] = "y2"

_STOP = frozenset({
    "year", "class", "grade", "book", "the", "of", "a", "an", "for", "part", "vol",
    "volume", "textbook", "pdf", "docx", "edition", "and", "my", "please",
})


def canon_tokens(text: str) -> list[str]:
    out: list[str] = []
    for t in re.findall(r"[^\W_]+", (text or "").lower()):
        if t in _STOP:
            continue
        out.append(_CANON.get(t, t))
    return out


def score_title(query_tokens: Sequence[str], title_tokens: Sequence[str]) -> float:
    """Share of query tokens found in the title (fuzzy), minus a small penalty per extra title token."""
    if not query_tokens or not title_tokens:
        return 0.0
    total = 0.0
    for q in query_tokens:
        best = 0.0
        for t in title_tokens:
            if q == t:
                best = 1.0
                break
            if len(q) >= 4 and len(t) >= 4:
                r = fuzz.ratio(q, t) / 100.0
                if r >= 0.8:
                    best = max(best, r)
        total += best
    extra = max(0, len(title_tokens) - len(query_tokens))
    return total / len(query_tokens) - 0.02 * extra


def _doc_tokens(doc) -> list[str]:
    seen: list[str] = []
    stem = (doc.filename or "").rsplit(".", 1)[0]
    for t in canon_tokens(doc.title) + canon_tokens(stem):
        if t not in seen:
            seen.append(t)
    return seen


async def resolve_document(query: str, db: AsyncSession):
    """Return (document, []) on a clear match, (None, [docs]) if ambiguous, (None, []) if none."""
    docs = (await db.execute(
        select(Document).where(Document.status == DocumentStatus.ready)
    )).scalars().all()
    qt = canon_tokens(query)
    scored = sorted(((score_title(qt, _doc_tokens(d)), d) for d in docs),
                    key=lambda x: (-x[0], -x[1].id))
    if not scored or scored[0][0] < MIN_DOC_SCORE:
        return None, []
    top = scored[0][0]
    close = [d for s, d in scored if s >= top - _AMBIGUITY_MARGIN]
    if len(close) > 1:
        return None, close
    return scored[0][1], []


async def list_titles(db: AsyncSession) -> list[str]:
    rows = await db.execute(
        select(Document.title).where(Document.status == DocumentStatus.ready)
        .order_by(Document.created_at.desc())
    )
    return [t for (t,) in rows.all()]


# ---------------------------------------------------------------- chapters
_TITLE_NUM = re.compile(r"^\s*(?:(?:chapter|unit|section|باب|فصل)\s*[:.\-]?\s*)?(\d{1,3})\b", re.I)


def title_number(title: str) -> int | None:
    m = _TITLE_NUM.match(title or "")
    return int(m.group(1)) if m else None


def _numbered(chapters) -> dict[int, object]:
    out: dict[int, object] = {}
    for ch in chapters:
        k = title_number(ch.title)
        if k is not None and k not in out:
            out[k] = ch
    return out


def pick_chapter(chapters, n: int):
    """Chapter 'n' as the student means it.

    If most titles carry numbers ("Chapter 13: Thermal Physics"), trust those.
    Otherwise use position (n-th chapter).
    """
    chapters = list(chapters)
    numbered = _numbered(chapters)
    if numbered and len(numbered) * 2 >= len(chapters):
        return numbered.get(n)
    if 1 <= n <= len(chapters):
        return chapters[n - 1]
    return None


def describe_range(chapters) -> str:
    chapters = list(chapters)
    if not chapters:
        return "It has no chapters."
    numbered = _numbered(chapters)
    if numbered and len(numbered) * 2 >= len(chapters):
        nums = sorted(numbered)
        return f"It has chapters {nums[0]} to {nums[-1]}."
    return f"It has {len(chapters)} chapters."