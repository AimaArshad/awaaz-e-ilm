"""Tests for chapter detection (contents page, drift, regex validation, filters)."""
import pytest

from app.services import chapters as ch

OPENER = "After studying this chapter, the students will be able to:\n@ Explain something\n"


def _book(n_pages, openers, contents_page_idx=2, contents=None):
    """Build fake page texts. `openers` are 0-based page indexes of chapter-opening pages."""
    pages = [f"Body text of page {i + 1}. " * 5 for i in range(n_pages)]
    for o in openers:
        pages[o] = OPENER + pages[o]
    pages[contents_page_idx] = contents
    return pages


PHYSICS_CONTENTS = (
    "CONTENTS\nChapter No.\nDescription\nPage No.\n"
    "Thermal Physics\n1\n1\nSimple Harmonic Motion\n2\n15\nPhysical Optics\n3\n42\n"
    "Electrostatics\n4\n57\nAlternating Current\n5\n81\nQuantum Physics\n6\n114\n"
    "Nuclear and Particle Physics\n7\n133\nMedical Physics\n8\n152\nSpace and Environment\n9\n165\n"
)


class TestParseContents:
    def test_table_layout(self):
        entries = ch.parse_contents(PHYSICS_CONTENTS)
        assert len(entries) == 9
        assert entries[0] == (1, "Thermal Physics", 1)
        assert entries[-1] == (9, "Space and Environment", 165)

    def test_dotted_layout(self):
        text = "Table of Contents\nIntroduction ........ 1\nMethods ........ 12\nResults ........ 30\n"
        entries = ch.parse_contents(text)
        assert [e[2] for e in entries] == [1, 12, 30]

    def test_rejects_non_ascending_pages(self):
        text = "CONTENTS\nA book\n1\n50\nB book\n2\n20\nC book\n3\n90\n"
        assert ch.parse_contents(text) == []

    def test_rejects_too_few_entries(self):
        assert ch.parse_contents("CONTENTS\nOnly One\n1\n1\n") == []


class TestContentsDetection:
    def test_constant_offset(self):
        # printed page p -> pdf page p+3 (0-based idx p+2)
        printed = [1, 15, 42, 57, 81, 114, 133, 152, 165]
        pages = _book(186, [p + 2 for p in printed], contents=PHYSICS_CONTENTS)
        result = ch.detect_from_contents_text(pages)
        assert result is not None and len(result) == 9
        assert [c.page_start for c in result] == [p + 2 for p in printed]
        assert result[0].title == "Chapter 1: Thermal Physics"
        assert result[-1].page_end == 185
        assert all(c.detection_method == "contents" for c in result)

    def test_offset_drift_midway(self):
        # same as the real book: offset 3 for chapters 1-3, then 4 (an extra page)
        printed = [1, 15, 42, 57, 81, 114, 133, 152, 165]
        idx = [p + 2 for p in printed[:3]] + [p + 3 for p in printed[3:]]
        pages = _book(186, idx, contents=PHYSICS_CONTENTS)
        result = ch.detect_from_contents_text(pages)
        assert result is not None
        assert [c.page_start for c in result] == idx
        # ranges are contiguous and cover the book from chapter 1 to the end
        for a, b in zip(result, result[1:]):
            assert b.page_start == a.page_end + 1

    def test_no_contents_page_returns_none(self):
        pages = ["just text " * 20 for _ in range(30)]
        assert ch.detect_from_contents_text(pages) is None

    def test_untrusted_when_openers_not_found(self):
        pages = _book(186, [], contents=PHYSICS_CONTENTS)   # no opener pages at all
        assert ch.detect_from_contents_text(pages) is None

    def test_title_fallback_when_no_opener_phrase(self):
        contents = "CONTENTS\nAlpha Topic\n1\n1\nBeta Topic\n2\n10\nGamma Topic\n3\n20\n"
        pages = _book(40, [], contents=contents)
        for start, name in [(3, "Alpha Topic"), (12, "Beta Topic"), (22, "Gamma Topic")]:
            pages[start] = f"{name}\nIntro text here. " + pages[start]
        result = ch.detect_from_contents_text(pages)
        assert result is not None
        assert [c.page_start for c in result] == [3, 12, 22]


class TestRegexValidation:
    def test_accepts_increasing_chapters(self):
        text = "Chapter 1: One\nbody\nChapter 2: Two\nbody\nChapter 3: Three\nbody"
        result = ch.detect_from_regex(text)
        assert result is not None and len(result) == 3

    def test_rejects_repeated_running_header(self):
        text = "Chapter 5\nbody\nChapter 5\nbody\nChapter 5\nbody"
        assert ch.detect_from_regex(text) is None

    def test_urdu_headings(self):
        text = "باب 1\nمتن\nباب 2\nمتن\nباب 3\nمتن"
        result = ch.detect_from_regex(text)
        assert result is not None and len(result) == 3

    def test_number_words(self):
        text = "CHAPTER ONE\nx\nCHAPTER TWO\ny"
        assert len(ch.detect_from_regex(text)) == 2


class TestTitleFilter:
    @pytest.mark.parametrize("title", [
        "ma=-kx", "ToneEenmE", "W Prysics 1)", "KE. =( 2) mv", "@ Soyoutnow?", "oo PR",
        "Short Answer Questions", "Numerical Problems", "Chapter", "[Physics 19) |",
        "66310 Js", "",
    ])
    def test_rejects_garbage(self, title):
        assert not ch._is_plausible_title(title)

    @pytest.mark.parametrize("title", [
        "Simple Harmonic Motion", "Alternating Current", "Thermal Physics",
    ])
    def test_accepts_real_titles(self, title):
        assert ch._is_plausible_title(title)


class TestSplitChaptersFallback:
    def test_text_only_uses_regex(self):
        text = "Chapter 1: A\nbody\nChapter 2: B\nbody"
        out = ch.split_chapters(text, file_type="docx")
        assert len(out) == 2 and out[0]["detection_method"] == "regex"

    def test_plain_text_uses_fallback(self):
        out = ch.split_chapters("hello world " * 10, file_type="png")
        assert len(out) == 1 and out[0]["detection_method"] == "fallback"

    def test_long_pdf_without_structure_uses_15_page_sections(self):
        pages = ["some ordinary text on this page. " * 10 for _ in range(40)]
        out = ch.split_chapters("\n".join(pages), pages_text=pages, file_type="pdf", file_path=None)
        assert out[0]["detection_method"] == "fallback"
        assert len(out) == 3   # 40 pages / 15 per section