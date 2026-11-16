"""Chapter detection and splitting service.

Detection strategies (tried in order, first valid result wins):

PDF:   1. TOC            - built-in bookmarks (``doc.get_toc()``)
       2. CONTENTS page  - parse the book's own contents list, find the page
                           offset automatically and follow drift between chapters
       3. Regex headings - ``Chapter N``, ``Unit N``, ``باب N`` ... (validated)
       4. Font heuristic - big heading text, with strict noise filters
       5. Fallback       - page chunks named ``Section 1, 2, ...``
DOCX:  heading styles -> regex -> text chunks
Other: regex -> text chunks

Each chapter dict carries:
    ``index``, ``title``, ``text``, ``language``, ``page_start``, ``page_end``,
    ``detection_method``.   (page numbers are 0-based, like before)

Design rule: a short, correct chapter list is better than a long, wrong one.
When a strategy is not confident it returns ``None`` and the next one runs.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class ChapterInfo:
    """Detected chapter with metadata."""
    index: int
    title: str
    text: str
    language: str = "en"
    page_start: int = 0
    page_end: int = 0
    detection_method: str = ""  # "toc", "contents", "docx_heading", "regex", "font", "fallback"


# ============================================================================
# Number-word mapping (English & Urdu)
# ============================================================================

_EN_NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22,
    "twenty-three": 23, "twenty-four": 24, "twenty-five": 25,
    "thirty": 30, "forty": 40, "fifty": 50,
}

_UR_NUMBER_WORDS: dict[str, int] = {
    "ایک": 1, "دو": 2, "تین": 3, "چار": 4, "پانچ": 5,
    "چھ": 6, "سات": 7, "آٹھ": 8, "نو": 9, "دس": 10,
    "گیارہ": 11, "بارہ": 12, "تیرہ": 13, "چودہ": 14, "پندرہ": 15,
    "سولہ": 16, "سترہ": 17, "اٹھارہ": 18, "انیس": 19, "بیس": 20,
}

# Eastern Arabic-Indic digits  ٠١٢٣٤٥٦٧٨٩  and Persian/Urdu digits ۰۱۲۳۴۵۶۷۸۹
_EASTERN_ARABIC_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _parse_number(s: str) -> Optional[int]:
    """Parse a number from a string: digit, English word, Urdu word or Eastern Arabic digits."""
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        try:
            return int(s)
        except ValueError:
            pass
    translated = s.translate(_EASTERN_ARABIC_MAP)
    if translated.isdigit():
        return int(translated)
    lower = s.lower()
    if lower in _EN_NUMBER_WORDS:
        return _EN_NUMBER_WORDS[lower]
    if s in _UR_NUMBER_WORDS:
        return _UR_NUMBER_WORDS[s]
    return None


# ============================================================================
# Shared helpers
# ============================================================================

def _open_pdf(file_path: str):
    """Open a PDF with PyMuPDF (new ``pymupdf`` name first, old ``fitz`` as fallback)."""
    try:
        import pymupdf as _mu
    except ImportError:  # pragma: no cover - older installs
        import fitz as _mu
    return _mu.open(file_path)


def _norm(s: str) -> str:
    """Lowercase and keep only letters/digits (Latin + Arabic script) for comparisons."""
    return re.sub(r"[^0-9a-z\u0600-\u06ff]+", "", (s or "").lower())


# Headings that are parts of a chapter, never chapters themselves.
_BLOCKED_HEADINGS = {
    "short answer questions", "numerical problems", "exercise", "exercises",
    "summary", "mcqs", "multiple choice questions", "constructed response questions",
    "review questions", "questions", "key points", "contents", "preface", "index",
    "glossary", "references", "chapter", "unit", "section", "part",
}
_BAD_TITLE_CHARS = set("=~@[]{}()|\\^<>")


def _is_plausible_title(title: str) -> bool:
    """Reject OCR garbage, equations, running headers' fragments and section headings."""
    t = (title or "").strip()
    if not 4 <= len(t) <= 120:
        return False
    if any(ch in _BAD_TITLE_CHARS for ch in t):
        return False
    non_space = [c for c in t if not c.isspace()]
    if not non_space:
        return False
    letters = sum(c.isalpha() for c in non_space)
    if letters / len(non_space) < 0.7:
        return False
    if t.lower().strip(" :.-") in _BLOCKED_HEADINGS:
        return False
    if re.search(r"[a-z][A-Z]", t):                      # "ToneEenmE": OCR garbage
        return False
    words = re.findall(r"[^\W\d_]+", t)
    if not any(len(w) >= 4 for w in words):               # "oo PR": no real word
        return False
    return True


def _join_pages(pages: Sequence[str], first: int, last: int) -> str:
    return "\n\n".join(
        pages[p] for p in range(first, last + 1)
        if 0 <= p < len(pages) and pages[p].strip()
    )


# ============================================================================
# Strategy 1: PDF TOC
# ============================================================================

def detect_from_toc(file_path: str, pages_text: list[str]) -> Optional[list[ChapterInfo]]:
    """Extract chapters from the PDF's built-in table of contents (bookmarks)."""
    try:
        doc = _open_pdf(file_path)
    except Exception:
        return None
    try:
        toc = doc.get_toc()
    finally:
        doc.close()

    if not toc:
        return None

    # TOC entries are [level, title, page_number (1-based)]; only level 1 are chapters
    level1 = [(title.strip(), page - 1) for level, title, page in toc
              if level == 1 and title.strip() and page >= 1]
    if not level1:
        return None

    total_pages = len(pages_text)
    chapters: list[ChapterInfo] = []
    for i, (title, page_start) in enumerate(level1):
        page_end = (level1[i + 1][1] - 1) if i + 1 < len(level1) else total_pages - 1
        page_end = min(page_end, total_pages - 1)
        page_start = min(page_start, total_pages - 1)
        chapters.append(ChapterInfo(
            index=i,
            title=title,
            text=_join_pages(pages_text, page_start, page_end),
            page_start=page_start,
            page_end=page_end,
            detection_method="toc",
        ))

    logger.info("Detected %d chapters from PDF TOC", len(chapters))
    return chapters


# ============================================================================
# Strategy 2: CONTENTS page  (printed contents list -> chapter start pages)
# ============================================================================
# The pure functions below work on a plain list of page texts, so they can be
# tested without any PDF file.

# Phrases that appear on the first page of a chapter in many textbooks.
_OPENER_PHRASES = (
    "after studying this chapter",
    "students will be able to",
    "student learning outcomes",
)
_OPENER_SCAN_CHARS = 800      # only look at the top of the page
_SNAP_WINDOW = 3              # +/- pages searched around the predicted start
_MAX_OFFSET = 14              # printed page 1 may sit up to this many pages into the PDF
_CONTENTS_SEARCH_PAGES = 15   # look for the CONTENTS page in the first N pages


def parse_contents(text: str) -> List[Tuple[int, str, int]]:
    """Parse a CONTENTS page into ``[(chapter_no, title, printed_page), ...]``.

    Supports two layouts:
      A) title / chapter number / page number on separate lines (table style)
      B) ``Title ........ 15`` on one line (optionally with a leading number)
    Returns ``[]`` unless at least 3 entries with ascending numbers and pages are found.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    entries: List[Tuple[int, str, int]] = []

    # Layout A
    i = 0
    while i < len(lines) - 2:
        t, a, b = lines[i], lines[i + 1], lines[i + 2]
        if (re.fullmatch(r"\d{1,3}", a) and re.fullmatch(r"\d{1,4}", b)
                and re.search(r"[A-Za-z\u0600-\u06FF]{3}", t) and not t.isdigit()):
            entries.append((int(a), t, int(b)))
            i += 3
        else:
            i += 1

    # Layout B
    if len(entries) < 3:
        entries = []
        n = 0
        for l in lines:
            m = re.match(r"^(?:(\d+)[.\s]+)?(.+?)[\s.·…_]{2,}(\d{1,4})$", l)
            if m:
                n += 1
                entries.append((int(m.group(1) or n), m.group(2).strip(), int(m.group(3))))

    nums = [e[0] for e in entries]
    pages = [e[2] for e in entries]
    ok = (len(entries) >= 3 and nums == sorted(nums) and pages == sorted(pages)
          and len(set(pages)) == len(pages) and len(set(nums)) == len(nums))
    return entries if ok else []


def find_contents(page_texts: Sequence[str],
                  max_pages: int = _CONTENTS_SEARCH_PAGES) -> Tuple[Optional[int], List[Tuple[int, str, int]]]:
    """Find the CONTENTS page. Returns ``(page_index, entries)`` or ``(None, [])``."""
    for p in range(min(max_pages, len(page_texts))):
        text = page_texts[p]
        if re.search(r"\bcontents\b|فہرست", text, re.IGNORECASE):
            entries = parse_contents(text)
            if entries:
                return p, entries
    return None, []


def _is_opener(page_text: str) -> bool:
    top = page_text[:_OPENER_SCAN_CHARS].lower()
    return any(p in top for p in _OPENER_PHRASES)


def _calibrate_offset(page_texts: Sequence[str], entries: Sequence[Tuple[int, str, int]]) -> Tuple[int, int]:
    """Starting offset (pdf_page = printed_page + offset) where most chapter starts are
    opener pages. Only opener phrases are scored (running headers caused false matches).
    Ties keep the lowest offset."""
    best, best_hits = 0, -1
    n = len(page_texts)
    for offset in range(0, _MAX_OFFSET + 1):
        hits = 0
        for _, _, printed in entries:
            idx = printed + offset - 1
            if 0 <= idx < n and _is_opener(page_texts[idx]):
                hits += 1
        if hits > best_hits:
            best, best_hits = offset, hits
    return best, best_hits


def _snap_start(page_texts: Sequence[str], guess: int, title: str,
                min_page: int = -1) -> Tuple[int, bool]:
    """Find the real first page of a chapter near ``guess`` (0-based).

    1) the closest page (within the window) that looks like an opener page;
    2) else the first page near the guess whose top contains the chapter title
       (and whose previous page's top does not: running headers repeat);
    3) else the guess itself, flagged as not found.
    """
    n = len(page_texts)
    lo, hi = guess - _SNAP_WINDOW, guess + _SNAP_WINDOW
    cands = sorted((c for c in range(lo, hi + 1) if 0 <= c < n and c > min_page),
                   key=lambda c: (abs(c - guess), c))
    for c in cands:
        if _is_opener(page_texts[c]):
            return c, True

    nt = _norm(title)
    if len(nt) >= 4:
        for c in sorted(cands):
            here = _norm(page_texts[c][:300])
            prev = _norm(page_texts[c - 1][:300]) if c - 1 > min_page else ""
            if nt in here and nt not in prev:
                return c, True
    return guess, False


def locate_chapter_starts(page_texts: Sequence[str],
                          entries: Sequence[Tuple[int, str, int]],
                          min_page: int = -1) -> Tuple[List[int], List[bool], int]:
    """Return ``(starts, found_flags, initial_offset)`` with 0-based start pages.

    The page offset is NOT assumed constant: whenever an opener page is found, the
    observed shift is carried forward as the prediction for the next chapter, so a
    book with an extra unnumbered page in the middle still works.
    """
    offset, _ = _calibrate_offset(page_texts, entries)
    shift = offset
    starts: List[int] = []
    flags: List[bool] = []
    for _, title, printed in entries:
        guess = printed + shift - 1
        idx, found = _snap_start(page_texts, guess, title, min_page)
        if starts and idx <= starts[-1]:          # starts must strictly increase
            idx, found = max(guess, starts[-1] + 1), False
        if found:
            shift = idx + 1 - printed
        starts.append(idx)
        flags.append(found)
    return starts, flags, offset


def detect_from_contents_page(file_path: str, pages_text: list[str]) -> Optional[list[ChapterInfo]]:
    """Build chapters from the book's printed CONTENTS page (PDF only)."""
    try:
        doc = _open_pdf(file_path)
    except Exception:
        return None
    try:
        raw_pages = [doc[i].get_text() for i in range(len(doc))]
    finally:
        doc.close()
    return detect_from_contents_text(raw_pages, pages_text)


def detect_from_contents_text(raw_pages: Sequence[str],
                              pages_text: Optional[Sequence[str]] = None) -> Optional[list[ChapterInfo]]:
    """Same as :func:`detect_from_contents_page` but on already-extracted page texts."""
    n = len(raw_pages)
    cpage, entries = find_contents(raw_pages)
    if not entries:
        return None

    starts, flags, offset = locate_chapter_starts(raw_pages, entries, min_page=cpage)

    if any(s >= n for s in starts):
        return None
    if len(set(starts)) != len(starts) or starts != sorted(starts):
        return None
    low_conf = sum(1 for f in flags if not f)
    if low_conf * 3 > len(entries):        # more than a third unconfirmed -> do not trust
        logger.info("Contents page found but %d/%d starts unconfirmed; skipping", low_conf, len(entries))
        return None

    source = pages_text if pages_text is not None and len(pages_text) == n else raw_pages
    chapters: list[ChapterInfo] = []
    for k, (no, title, _) in enumerate(entries):
        first = starts[k]
        last = starts[k + 1] - 1 if k + 1 < len(entries) else n - 1
        chapters.append(ChapterInfo(
            index=k,
            title=f"Chapter {no}: {title}",
            text=_join_pages(source, first, last),
            page_start=first,
            page_end=last,
            detection_method="contents",
        ))

    logger.info("Detected %d chapters from CONTENTS page (page %d, start offset %d, %d unconfirmed)",
                len(chapters), cpage + 1, offset, low_conf)
    return chapters


# ============================================================================
# Strategy 3: DOCX heading styles
# ============================================================================

def detect_from_docx_headings(file_path: str) -> Optional[list[ChapterInfo]]:
    """Extract chapters from DOCX heading styles (Heading 1, Heading 2, ...)."""
    try:
        from docx import Document as DocxDocument
    except ImportError:
        return None

    doc = DocxDocument(file_path)
    heading_indices: list[tuple[int, str]] = []
    paragraphs: list[str] = []

    for i, para in enumerate(doc.paragraphs):
        paragraphs.append(para.text)
        style_name = (para.style.name or "").lower()
        if style_name.startswith("heading") and para.text.strip():
            heading_indices.append((i, para.text.strip()))

    if not heading_indices:
        return None

    chapters: list[ChapterInfo] = []
    for idx, (para_idx, title) in enumerate(heading_indices):
        end_idx = heading_indices[idx + 1][0] if idx + 1 < len(heading_indices) else len(paragraphs)
        body_lines = paragraphs[para_idx + 1: end_idx]
        text = "\n".join(line for line in body_lines if line.strip())
        chapters.append(ChapterInfo(
            index=idx, title=title, text=text, detection_method="docx_heading",
        ))

    logger.info("Detected %d chapters from DOCX headings", len(chapters))
    return chapters


# ============================================================================
# Strategy 4: Regex heading patterns (validated)
# ============================================================================

_EN_NUM = r"(?:\d+|" + "|".join(re.escape(w) for w in _EN_NUMBER_WORDS) + r")"
_EN_PATTERNS = [
    re.compile(r"^(?:chapter)\s+(?P<num>" + _EN_NUM + r")(?:\s*[:.\-—]\s*(.*))?$",
               re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(?:unit)\s+(?P<num>" + _EN_NUM + r")(?:\s*[:.\-—]\s*(.*))?$",
               re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(?:section)\s+(?P<num>" + _EN_NUM + r")(?:\s*[:.\-—]\s*(.*))?$",
               re.IGNORECASE | re.MULTILINE),
]

_UR_NUM = r"(?:[\d٠-٩۰-۹]+|" + "|".join(re.escape(w) for w in _UR_NUMBER_WORDS) + r")"
_UR_PATTERNS = [
    re.compile(r"^(?:باب)\s+(?P<num>" + _UR_NUM + r")(?:\s*[:.\-—۔]\s*(.*))?$", re.MULTILINE),
    re.compile(r"^(?:فصل)\s+(?P<num>" + _UR_NUM + r")(?:\s*[:.\-—۔]\s*(.*))?$", re.MULTILINE),
]

_ALL_HEADING_PATTERNS = _EN_PATTERNS + _UR_PATTERNS


def detect_from_regex(text: str) -> Optional[list[ChapterInfo]]:
    """Detect chapters using heading patterns.

    A pattern is only accepted if the chapter numbers it finds are unique and strictly
    increasing; repeated running headers ("Chapter 5" on every page) are rejected.
    """
    for pattern in _ALL_HEADING_PATTERNS:
        matches = list(pattern.finditer(text))
        if not matches:
            continue

        numbers = [_parse_number(m.group("num")) for m in matches]
        if any(n is None for n in numbers):
            continue
        if any(b <= a for a, b in zip(numbers, numbers[1:])):
            continue

        chapters: list[ChapterInfo] = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chapters.append(ChapterInfo(
                index=i,
                title=m.group(0).strip()[:256],
                text=text[start:end].strip(),
                detection_method="regex",
            ))

        logger.info("Detected %d chapters via regex pattern %s", len(chapters), pattern.pattern[:40])
        return chapters
    return None


# ============================================================================
# Strategy 5: Font-size heuristic (PDF only, strict filters)
# ============================================================================

_MIN_CHAPTER_PAGES = 4        # a real chapter spans at least this many pages
_MIN_FONT_CHAPTERS = 3        # fewer than this -> not trustworthy


def detect_from_font_heuristics(file_path: str, pages_text: list[str]) -> Optional[list[ChapterInfo]]:
    """Detect chapters from large heading text near the top of pages.

    Candidates are filtered hard: repeated text (running headers), garbled or
    equation-like text, known section headings, and headings closer than
    ``_MIN_CHAPTER_PAGES`` to the previous one are all dropped. If fewer than
    ``_MIN_FONT_CHAPTERS`` survive, ``None`` is returned (the caller falls back to
    page chunks).
    """
    try:
        doc = _open_pdf(file_path)
    except Exception:
        return None

    try:
        total_pages = len(doc)
        if total_pages == 0:
            return None

        all_sizes: list[float] = []
        for page in doc:
            for block in page.get_text("dict", flags=0).get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            all_sizes.append(span.get("size", 12.0))
        if not all_sizes:
            return None

        threshold = (sum(all_sizes) / len(all_sizes)) * 1.3

        candidates: list[tuple[int, str]] = []
        for page_idx, page in enumerate(doc):
            top_limit = page.rect.height * 0.25
            found = None
            for block in page.get_text("dict", flags=0).get("blocks", []):
                if block.get("bbox", (0, 0, 0, 0))[1] > top_limit:
                    continue
                for line in block.get("lines", []):
                    spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
                    if spans and max(s.get("size", 12.0) for s in spans) >= threshold:
                        found = " ".join(s["text"].strip() for s in spans)
                        break
                if found:
                    break
            if found:
                candidates.append((page_idx, found))
    finally:
        doc.close()

    repeats = Counter(_norm(t) for _, t in candidates)
    kept: list[tuple[int, str]] = []
    for page_idx, title in candidates:
        if repeats[_norm(title)] >= 3:
            continue
        if not _is_plausible_title(title):
            continue
        if kept and page_idx - kept[-1][0] < _MIN_CHAPTER_PAGES:
            continue
        kept.append((page_idx, title))

    if len(kept) < _MIN_FONT_CHAPTERS:
        logger.info("Font heuristic found only %d plausible headings; not used", len(kept))
        return None

    chapters: list[ChapterInfo] = []
    for i, (page_idx, title) in enumerate(kept):
        page_end = (kept[i + 1][0] - 1) if i + 1 < len(kept) else len(pages_text) - 1
        page_end = min(page_end, len(pages_text) - 1)
        chapters.append(ChapterInfo(
            index=i, title=title[:256], text=_join_pages(pages_text, page_idx, page_end),
            page_start=page_idx, page_end=page_end, detection_method="font",
        ))

    logger.info("Detected %d chapters from font heuristics", len(chapters))
    return chapters


# ============================================================================
# Strategy 6: Fallback - chunks
# ============================================================================

def fallback_page_chunks(pages_text: list[str], pages_per_chunk: int = 5) -> list[ChapterInfo]:
    """Split pages into fixed-size chunks (always returns at least one)."""
    if not pages_text:
        return [ChapterInfo(index=0, title="Section 1", text="", detection_method="fallback")]

    chapters: list[ChapterInfo] = []
    for i in range(0, len(pages_text), pages_per_chunk):
        text = "\n\n".join(p for p in pages_text[i:i + pages_per_chunk] if p.strip())
        if not text.strip():
            continue
        chapters.append(ChapterInfo(
            index=len(chapters),
            title=f"Section {len(chapters) + 1}",
            text=text,
            page_start=i,
            page_end=min(i + pages_per_chunk - 1, len(pages_text) - 1),
            detection_method="fallback",
        ))

    if not chapters:
        chapters.append(ChapterInfo(
            index=0, title="Section 1", text="\n\n".join(pages_text),
            page_start=0, page_end=max(0, len(pages_text) - 1), detection_method="fallback",
        ))

    logger.info("Fallback: split into %d sections of %d pages each", len(chapters), pages_per_chunk)
    return chapters


def fallback_text_chunks(text: str, max_chars: int = 10_000) -> list[ChapterInfo]:
    """Split flat text into character-based chunks (DOCX, images, no page structure)."""
    if not text.strip():
        return [ChapterInfo(index=0, title="Section 1", text="", detection_method="fallback")]

    chunks = [text[i:i + max_chars] for i in range(0, len(text), max_chars)]
    return [
        ChapterInfo(index=i, title=f"Section {i + 1}", text=chunk.strip(), detection_method="fallback")
        for i, chunk in enumerate(chunks) if chunk.strip()
    ]


# ============================================================================
# Language detection helper
# ============================================================================

def _detect_chapter_lang(text: str, default: str = "en") -> str:
    """Detect the dominant language of a chapter's text."""
    try:
        from app.services.lang_detect import detect_language
        return detect_language(text[:500], default=default)
    except Exception:
        return default


# ============================================================================
# Public API
# ============================================================================

_PDF_FALLBACK_PAGES_PER_CHUNK = 15   # long books: sections of about 15 pages


def split_chapters(
    text: str,
    *,
    file_path: Optional[str] = None,
    pages_text: Optional[list[str]] = None,
    file_type: str = "",
    default_lang: str = "en",
    max_chars_per_chapter: int = 10_000,
) -> list[dict]:
    """Split a document into chapters using the best available strategy.

    Returns a list of dicts with keys: ``index``, ``title``, ``text``, ``language``,
    ``page_start``, ``page_end``, ``detection_method``.
    """
    chapters: Optional[list[ChapterInfo]] = None
    is_pdf = bool(file_path) and file_type == "pdf" and pages_text is not None

    if is_pdf:
        chapters = detect_from_toc(file_path, pages_text)
        if chapters is None:
            chapters = detect_from_contents_page(file_path, pages_text)

    if chapters is None and file_path and file_type == "docx":
        chapters = detect_from_docx_headings(file_path)

    if chapters is None:
        chapters = detect_from_regex(text)

    if chapters is None and is_pdf:
        chapters = detect_from_font_heuristics(file_path, pages_text)

    if chapters is None:
        if pages_text is not None and len(pages_text) > 1:
            chapters = fallback_page_chunks(pages_text, pages_per_chunk=_PDF_FALLBACK_PAGES_PER_CHUNK)
        else:
            chapters = fallback_text_chunks(text, max_chars=max_chars_per_chapter)

    for ch in chapters:
        ch.language = _detect_chapter_lang(ch.text, default=default_lang)

    return [
        {
            "index": ch.index,
            "title": ch.title,
            "text": ch.text,
            "language": ch.language,
            "page_start": ch.page_start,
            "page_end": ch.page_end,
            "detection_method": ch.detection_method,
        }
        for ch in chapters
    ]