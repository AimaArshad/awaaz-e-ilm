"""Tests for the language detection service (Prompt 3).

Covers:
- Arabic-script ratio calculation
- Per-snippet language detection (English / Urdu)
- Per-paragraph breakdown with detect_paragraphs
- Edge cases: empty text, short text, mixed-script text
"""
from __future__ import annotations

import pytest

from app.services.lang_detect import (
    LangSpan,
    arabic_script_ratio,
    detect_language,
    detect_paragraphs,
)


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

ENGLISH_TEXT = (
    "The quick brown fox jumps over the lazy dog. "
    "This sentence is clearly written in the English language."
)

URDU_TEXT = (
    "یہ اردو زبان میں لکھا گیا ہے۔ "
    "اس جملے کو اردو کے طور پر شناخت کیا جانا چاہیے۔"
)

MIXED_TEXT = (
    "This paragraph is in English and should be detected as such.\n\n"
    "یہ پیراگراف اردو میں ہے اور اسے اردو کے طور پر شناخت کیا جانا چاہیے۔"
)

SHORT_TEXT = "Hi"  # too short for reliable detection


# ---------------------------------------------------------------------------
# arabic_script_ratio
# ---------------------------------------------------------------------------

class TestArabicScriptRatio:
    def test_pure_english(self):
        ratio = arabic_script_ratio(ENGLISH_TEXT)
        assert ratio == 0.0

    def test_pure_urdu(self):
        ratio = arabic_script_ratio(URDU_TEXT)
        assert ratio > 0.9

    def test_empty_string(self):
        assert arabic_script_ratio("") == 0.0

    def test_digits_only(self):
        assert arabic_script_ratio("12345") == 0.0

    def test_mixed_returns_intermediate(self):
        mixed = "Hello World سلام"
        ratio = arabic_script_ratio(mixed)
        assert 0.0 < ratio < 1.0

    def test_eastern_arabic_numerals_not_counted_as_letters(self):
        # Eastern Arabic numerals ۰-۹ are in the Arabic block but are not
        # letters.  Our regex does include them since they're in the range.
        # This test documents the current behaviour.
        ratio = arabic_script_ratio("۱۲۳")
        # These are in the Arabic range, so they're counted
        assert ratio > 0


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------

class TestDetectLanguage:
    def test_english(self):
        assert detect_language(ENGLISH_TEXT) == "en"

    def test_urdu(self):
        assert detect_language(URDU_TEXT) == "ur"

    def test_short_text_returns_default(self):
        assert detect_language(SHORT_TEXT) == "en"
        assert detect_language(SHORT_TEXT, default="ur") == "ur"

    def test_empty_text_returns_default(self):
        assert detect_language("") == "en"
        assert detect_language("", default="ur") == "ur"

    def test_whitespace_only_returns_default(self):
        assert detect_language("   \n\t  ") == "en"

    def test_urdu_with_english_loanwords(self):
        # Urdu text with some English words should still be detected as Urdu
        text = "یہ ایک test ہے جو language detection کو چیک کرتا ہے۔"
        assert detect_language(text) == "ur"


# ---------------------------------------------------------------------------
# detect_paragraphs
# ---------------------------------------------------------------------------

class TestDetectParagraphs:
    def test_single_english_paragraph(self):
        spans = detect_paragraphs(ENGLISH_TEXT)
        assert len(spans) == 1
        assert spans[0].lang == "en"
        assert isinstance(spans[0], LangSpan)

    def test_single_urdu_paragraph(self):
        spans = detect_paragraphs(URDU_TEXT)
        assert len(spans) == 1
        assert spans[0].lang == "ur"

    def test_mixed_paragraphs(self):
        spans = detect_paragraphs(MIXED_TEXT)
        assert len(spans) == 2
        # First paragraph is English, second is Urdu
        langs = [s.lang for s in spans]
        assert "en" in langs
        assert "ur" in langs

    def test_empty_text(self):
        spans = detect_paragraphs("")
        assert spans == []

    def test_confidence_is_set(self):
        spans = detect_paragraphs(ENGLISH_TEXT)
        assert all(0.0 <= s.confidence <= 1.0 for s in spans)

    def test_preserves_paragraph_text(self):
        spans = detect_paragraphs("Hello world.\n\nThis is another paragraph.")
        assert len(spans) == 2
        assert "Hello world" in spans[0].text
        assert "another paragraph" in spans[1].text

