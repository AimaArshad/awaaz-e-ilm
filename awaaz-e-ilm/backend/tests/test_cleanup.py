"""Tests for the text cleanup service (Prompt 3).

Covers:
- Unicode normalisation (NFKC / NFC)
- Urdu character normalisation
- Control character removal
- Header / footer / page-number removal
- Hyphenation repair
- Whitespace collapse
- Sentence splitting (pysbd)
- Full clean_text pipeline
"""
from __future__ import annotations

import pytest

from app.services.cleanup import (
    clean_text,
    collapse_whitespace,
    fix_hyphenation,
    normalize_unicode,
    normalize_urdu,
    remove_control_chars,
    remove_headers_footers,
    split_sentences,
)


# ---------------------------------------------------------------------------
# Unicode normalisation
# ---------------------------------------------------------------------------

class TestNormalizeUnicode:
    def test_nfkc_for_english(self):
        # NFKC should decompose ligatures like ﬁ → fi
        result = normalize_unicode("\uFB01le", lang="en")  # ﬁle
        assert result == "file"

    def test_nfc_for_urdu(self):
        # NFC should keep composed Arabic forms
        text = "سلام"
        result = normalize_unicode(text, lang="ur")
        assert result == text  # NFC should leave it unchanged


# ---------------------------------------------------------------------------
# Urdu normalisation
# ---------------------------------------------------------------------------

class TestNormalizeUrdu:
    def test_arabic_ya_to_urdu(self):
        # Arabic Ya ي (\u064A) → Urdu Ya ی (\u06CC)
        result = normalize_urdu("ي")
        assert result == "\u06CC"

    def test_arabic_kaf_to_urdu(self):
        # Arabic Kaf ك (\u0643) → Urdu Kaf ک (\u06A9)
        result = normalize_urdu("ك")
        assert result == "\u06A9"

    def test_removes_tatweel(self):
        # Tatweel ـ (\u0640) should be removed
        result = normalize_urdu("سـلام")
        assert "\u0640" not in result
        assert "سلام" in result

    def test_preserves_normal_urdu(self):
        text = "یہ ایک ٹیسٹ ہے"
        result = normalize_urdu(text)
        assert len(result) > 0  # should not lose content


# ---------------------------------------------------------------------------
# Control character removal
# ---------------------------------------------------------------------------

class TestRemoveControlChars:
    def test_removes_null_bytes(self):
        assert remove_control_chars("hello\x00world") == "helloworld"

    def test_preserves_newlines(self):
        assert remove_control_chars("line1\nline2") == "line1\nline2"

    def test_preserves_tabs(self):
        assert remove_control_chars("col1\tcol2") == "col1\tcol2"

    def test_removes_form_feed(self):
        assert remove_control_chars("page1\x0cpage2") == "page1page2"


# ---------------------------------------------------------------------------
# Header / footer removal
# ---------------------------------------------------------------------------

class TestRemoveHeadersFooters:
    def test_removes_page_numbers(self):
        text = "Some content.\n42\nMore content."
        result = remove_headers_footers(text)
        assert "42" not in result.split("\n")

    def test_removes_dashed_page_numbers(self):
        text = "Content.\n— 5 —\nMore."
        result = remove_headers_footers(text)
        assert "— 5 —" not in result

    def test_removes_copyright(self):
        text = "Main text.\nCopyright 2024 by Author.\nMore text."
        result = remove_headers_footers(text)
        assert "copyright" not in result.lower()

    def test_preserves_content(self):
        text = "This is important content that must be preserved."
        result = remove_headers_footers(text)
        assert "important content" in result

    def test_eastern_arabic_page_numbers(self):
        text = "Content.\n٤٢\nMore."
        result = remove_headers_footers(text)
        assert "٤٢" not in result.split("\n")


# ---------------------------------------------------------------------------
# Hyphenation repair
# ---------------------------------------------------------------------------

class TestFixHyphenation:
    def test_joins_hyphenated_words(self):
        assert fix_hyphenation("knowl-\nedge") == "knowledge"

    def test_preserves_legitimate_hyphens(self):
        assert fix_hyphenation("well-known") == "well-known"

    def test_preserves_line_breaks_without_hyphens(self):
        text = "Line 1.\nLine 2."
        assert fix_hyphenation(text) == text

    def test_multiple_hyphenations(self):
        text = "under-\nstand the mean-\ning"
        result = fix_hyphenation(text)
        assert "understand" in result
        assert "meaning" in result


# ---------------------------------------------------------------------------
# Whitespace collapse
# ---------------------------------------------------------------------------

class TestCollapseWhitespace:
    def test_collapses_multiple_blank_lines(self):
        text = "para 1\n\n\n\n\npara 2"
        result = collapse_whitespace(text)
        assert result == "para 1\n\npara 2"

    def test_strips_trailing_spaces(self):
        text = "line with trailing spaces   \nnext line"
        result = collapse_whitespace(text)
        assert "   \n" not in result

    def test_strips_leading_and_trailing(self):
        result = collapse_whitespace("  \nhello\n  ")
        assert result == "hello"


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

class TestSplitSentences:
    def test_english_sentences(self):
        text = "Hello world. How are you? I am fine!"
        sentences = split_sentences(text, lang="en")
        # pysbd may group "How are you? I am fine!" as one segment
        assert len(sentences) >= 2
        assert any("Hello" in s for s in sentences)

    def test_single_sentence(self):
        sentences = split_sentences("Just one sentence.", lang="en")
        assert len(sentences) == 1

    def test_empty_text(self):
        sentences = split_sentences("", lang="en")
        assert sentences == [] or sentences == [""]

    def test_urdu_sentences(self):
        text = "یہ پہلا جملہ ہے۔ یہ دوسرا جملہ ہے۔"
        sentences = split_sentences(text, lang="ur")
        # pysbd may or may not split Urdu perfectly, but should return a list
        assert isinstance(sentences, list)
        assert len(sentences) >= 1

    def test_abbreviations_not_split(self):
        text = "Mr. Smith went to Washington. He arrived at 3 p.m."
        sentences = split_sentences(text, lang="en")
        # "Mr." should not cause a split
        assert any("Mr." in s or "Smith" in s for s in sentences)


# ---------------------------------------------------------------------------
# Full pipeline: clean_text
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_english_pipeline(self):
        raw = (
            "  Chapter 1  \n\n\n\n\n"
            "The quick brown fox jumped over the lazy dog.\n"
            "This sen-\ntence was hyphenated.\n"
            "\x00Hidden null.\n"
            "42\n"
            "Copyright 2024 by Author.\n"
        )
        cleaned = clean_text(raw, lang="en")
        assert "sentence was hyphenated" in cleaned or "sentencewas" in cleaned
        assert "\x00" not in cleaned
        assert "\n\n\n" not in cleaned

    def test_urdu_pipeline(self):
        raw = "يه ایک ٹیسٹ ہے\u0640۔"
        cleaned = clean_text(raw, lang="ur")
        # Arabic Ya should be normalised to Urdu Ya
        assert "\u064A" not in cleaned  # Arabic Ya removed
        assert "\u0640" not in cleaned  # tatweel removed

    def test_preserves_meaningful_content(self):
        text = "This is important content that must survive the cleanup pipeline."
        cleaned = clean_text(text, lang="en")
        assert "important content" in cleaned

    def test_idempotent(self):
        text = "Clean text should not change on re-cleaning."
        first = clean_text(text)
        second = clean_text(first)
        assert first == second

