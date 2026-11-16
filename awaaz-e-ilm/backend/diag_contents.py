import re
import sys
import pymupdf

OPENER_HINTS = ("after studying this chapter", "students will be able to")


def parse_contents(text):
    """Return [(chapter_no, title, printed_page)] from a CONTENTS page."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    entries = []

    # Format A: title / chapter no / page no on separate lines
    i = 0
    while i < len(lines) - 2:
        t, a, b = lines[i], lines[i + 1], lines[i + 2]
        if (re.fullmatch(r"\d{1,3}", a) and re.fullmatch(r"\d{1,4}", b)
                and re.search(r"[A-Za-z\u0600-\u06FF]{3}", t) and not t.isdigit()):
            entries.append((int(a), t, int(b)))
            i += 3
        else:
            i += 1

    # Format B: "Title ........ 15" on one line
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
    valid = (len(entries) >= 3 and nums == sorted(nums) and pages == sorted(pages)
             and len(set(pages)) == len(pages))
    return entries if valid else []


def find_contents(doc, max_pages=15):
    for p in range(min(max_pages, len(doc))):
        text = doc[p].get_text()
        if re.search(r"\bcontents\b", text, re.IGNORECASE):
            entries = parse_contents(text)
            if entries:
                return p, entries
    return None, []


def is_opener(doc, idx):
    if not 0 <= idx < len(doc):
        return False
    t = doc[idx].get_text().lower()
    return any(h in t for h in OPENER_HINTS)


def calibrate_offset(doc, entries):
    """Offset (pdf_page = printed + offset) where most chapter starts are opener pages.
    Only opener phrases are scored: running headers caused false matches before."""
    best, best_hits = 0, -1
    for offset in range(0, 11):
        hits = sum(is_opener(doc, printed + offset - 1) for _, _, printed in entries)
        if hits > best_hits:  # strict > keeps the lowest offset on ties
            best, best_hits = offset, hits
    return best, best_hits


# def snap_start(doc, idx):
#     """idx is the computed 0-based start. Prefer a nearby page that looks like an opener."""
#     for cand in (idx, idx - 1, idx + 1):
#         if is_opener(doc, cand):
#             return cand
#     return idx


# if __name__ == "__main__":
#     doc = pymupdf.open(sys.argv[1])
#     cpage, entries = find_contents(doc)
#     if not entries:
#         print("No usable CONTENTS page found")
#         sys.exit(1)
#     offset, hits = calibrate_offset(doc, entries)
#     print(f"contents on PDF page {cpage + 1}; offset={offset}; opener_hits={hits}/{len(entries)}")

#     starts = [snap_start(doc, printed + offset - 1) + 1 for _, _, printed in entries]  # 1-based
#     for k, (no, title, _) in enumerate(entries):
#         end = starts[k + 1] - 1 if k + 1 < len(entries) else len(doc)
#         print(f"  Chapter {no}: {title!r}  PDF pages {starts[k]}-{end}")


def snap_start(doc, guess_idx, window=3):
    """Find the opener page closest to the guess (0-based). Returns (idx, found)."""
    candidates = sorted(range(guess_idx - window, guess_idx + window + 1),
                        key=lambda c: (abs(c - guess_idx), c))
    for c in candidates:
        if is_opener(doc, c):
            return c, True
    return guess_idx, False


if __name__ == "__main__":
    doc = pymupdf.open(sys.argv[1])
    cpage, entries = find_contents(doc)
    if not entries:
        print("No usable CONTENTS page found")
        sys.exit(1)
    offset, hits = calibrate_offset(doc, entries)
    print(f"contents on PDF page {cpage + 1}; starting offset={offset}; opener_hits={hits}/{len(entries)}")

    shift = offset
    starts, found_flags = [], []
    for _, _, printed in entries:
        guess = printed + shift - 1
        idx, found = snap_start(doc, guess)
        if starts and idx + 1 <= starts[-1]:      # starts must keep increasing
            idx, found = guess, False
        if found:
            shift = idx + 1 - printed             # carry the drift to the next chapter
        starts.append(idx + 1)
        found_flags.append(found)

    for k, (no, title, _) in enumerate(entries):
        end = starts[k + 1] - 1 if k + 1 < len(entries) else len(doc)
        flag = "" if found_flags[k] else "  (low confidence)"
        print(f"  Chapter {no}: {title!r}  PDF pages {starts[k]}-{end}{flag}")