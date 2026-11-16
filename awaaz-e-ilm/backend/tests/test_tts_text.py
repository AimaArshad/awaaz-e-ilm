"""Tests for app.services.tts_text — text preparation for TTS.

Covers every rule specified in the requirements:
- Diagram noise filtering (low letter ratio, short non-words)
- Equation-only line filtering
- Figure/table reference removal
- Bullet glyph removal
- Symbol expansion (°C, %, m/s, etc.)
- Sentence re-joining and splitting
- Sentence length limiting (300 chars)
- Character cap (AUDIO_MAX_CHARS) with truncation
"""
from __future__ import annotations

import pytest

from app.services.tts_text import (
    PreparedText,
    _clean_line,
    _expand_symbols,
    _is_diagram_noise,
    _is_equation_line,
    _letter_ratio,
    _split_long_sentence,
    prepare_for_speech,
)


# ===========================================================================
# Diagram noise
# ===========================================================================

class TestDiagramNoise:
    """Lines that should be dropped as diagram/table noise."""

    @pytest.mark.parametrize("line", [
        "ToneEenmE",      # OCR garble, mixed-case noise
        "RS",             # 2-letter non-word
        "ea",             # 2-letter non-word
        "@3 ",            # symbol-heavy
        "| chapter",      # pipe symbol drops letter ratio
        "---",            # all dashes
        "|---|---|",       # table border
        "* * *",          # decorative
        ">>",             # arrows
    ])
    def test_noise_lines_are_dropped(self, line):
        assert _is_diagram_noise(line), f"Should be noise: {line!r}"

    @pytest.mark.parametrize("line", [
        "The quick brown fox jumps over the lazy dog.",
        "This is a normal sentence about physics.",
        "Energy is conserved in all processes.",
        "I",               # single letter but a real word
        "a",               # article
    ])
    def test_clean_lines_are_kept(self, line):
        assert not _is_diagram_noise(line), f"Should NOT be noise: {line!r}"


# ===========================================================================
# Equation detection
# ===========================================================================

class TestEquationDetection:
    """Lines dominated by equations should be dropped."""

    @pytest.mark.parametrize("line", [
        "ma=-kx",
        "KE. = 1/2 mv2",
        "F = ma",
        "E = mc2",
        "v = u + at",
    ])
    def test_equation_lines_are_dropped(self, line):
        assert _is_equation_line(line), f"Should be equation: {line!r}"

    @pytest.mark.parametrize("line", [
        "The force equals mass times acceleration.",
        "Energy is measured in joules.",
        "Newton discovered gravity.",
    ])
    def test_normal_text_is_kept(self, line):
        assert not _is_equation_line(line), f"Should NOT be equation: {line!r}"


# ===========================================================================
# Letter ratio
# ===========================================================================

class TestLetterRatio:
    def test_all_letters(self):
        assert _letter_ratio("hello") == 1.0

    def test_mixed(self):
        ratio = _letter_ratio("a1b2")
        assert 0.4 < ratio < 0.6

    def test_empty(self):
        assert _letter_ratio("") == 0.0

    def test_all_numbers(self):
        assert _letter_ratio("12345") == 0.0


# ===========================================================================
# Figure/table reference removal
# ===========================================================================

class TestFigTableRefs:
    # @pytest.mark.parametrize("text,expected", [
    #     ("See (Fig 13.1) for details.", "See  for details."),
    #     ("Shown in (Figure 2) above.", "Shown in  above."),
    #     ("Refer to (Table 3.1) below.", "Refer to  below."),
    #     ("As in Fig. 5 the curve...", "As in  the curve..."),
    # ])
    @pytest.mark.parametrize("text,expected", [
    ("See (Fig 13.1) for details.", "See for details."),
    ("Shown in (Figure 2) above.", "Shown in above."),
    ("Refer to (Table 3.1) below.", "Refer to below."),
    ("As in Fig. 5 the curve...", "As in the curve..."),
])
    def test_refs_removed(self, text, expected):
        result = _clean_line(text)
        assert result == expected.strip()


# ===========================================================================
# Bullet glyph removal
# ===========================================================================

class TestBulletGlyphs:
    @pytest.mark.parametrize("text,expected_contains", [
        ("• First point", "First point"),
        ("@ Second point", "Second point"),
        ("◆ Third point", "Third point"),
    ])
    def test_bullets_removed(self, text, expected_contains):
        result = _clean_line(text)
        assert expected_contains in result
        assert "•" not in result
        assert "@" not in result


# ===========================================================================
# Symbol expansion
# ===========================================================================

class TestSymbolExpansion:
    @pytest.mark.parametrize("text,expected_substr", [
        ("Water boils at 100°C", "degrees Celsius"),
        ("The efficiency is 85%", "percent"),
        ("Speed was 5 m/s", "metres per second"),
        ("Acceleration is 9.8 m/s²", "metres per second squared"),
        ("50 Hz frequency", "hertz"),
        ("5 kg of mass", "kilograms"),
        ("10 N force", "10 newtons"),
        ("100 J energy", "100 joules"),
        ("60 W power", "60 watts"),
    ])
    def test_symbols_expanded(self, text, expected_substr):
        result = _expand_symbols(text)
        assert expected_substr in result, f"Expected '{expected_substr}' in '{result}'"


# ===========================================================================
# Sentence length limiting
# ===========================================================================

class TestSentenceLengthLimiting:
    def test_short_sentence_unchanged(self):
        short = "This is a short sentence."
        result = _split_long_sentence(short)
        assert result == [short]

    def test_long_sentence_split_on_commas(self):
        # Build a sentence > 300 chars with commas
        parts = [f"this is part number {i} of the sentence" for i in range(15)]
        long_sentence = ", ".join(parts) + "."
        assert len(long_sentence) > 300
        result = _split_long_sentence(long_sentence)
        assert len(result) > 1
        assert all(len(s) <= 300 for s in result)


# ===========================================================================
# Full pipeline: prepare_for_speech
# ===========================================================================

class TestPrepareForSpeech:
    def test_basic_paragraph(self):
        text = "The sun rises in the east. It sets in the west."
        result = prepare_for_speech(text, lang="en")
        assert isinstance(result, PreparedText)
        assert len(result.paragraphs) >= 1
        all_sentences = [s for p in result.paragraphs for s in p]
        assert len(all_sentences) >= 2
        assert not result.truncated

    def test_noise_lines_filtered(self):
        text = "Normal text here.\n| chapter\n@3 \nToneEenmE\nMore normal text."
        result = prepare_for_speech(text, lang="en")
        all_text = " ".join(s for p in result.paragraphs for s in p)
        assert "ToneEenmE" not in all_text
        assert "@3" not in all_text
        assert "| chapter" not in all_text
        assert "Normal text" in all_text

    def test_equations_filtered(self):
        text = "Newton's second law states.\nF = ma\nThis is important."
        result = prepare_for_speech(text, lang="en")
        all_text = " ".join(s for p in result.paragraphs for s in p)
        assert "F = ma" not in all_text
        assert "important" in all_text

    def test_truncation_at_max_chars(self, monkeypatch):
        """Text exceeding AUDIO_MAX_CHARS should be truncated at a sentence boundary."""
        monkeypatch.setenv("AUDIO_MAX_CHARS", "100")
        # Clear settings cache so new env var is picked up
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            text = "This is sentence one. " * 20  # ~440 chars
            result = prepare_for_speech(text, lang="en")
            assert result.truncated
            assert result.total_chars <= 110  # ~100 + one sentence overshoot
        finally:
            monkeypatch.delenv("AUDIO_MAX_CHARS", raising=False)
            get_settings.cache_clear()

    def test_paragraphs_preserved(self):
        text = "First paragraph sentence one. First paragraph sentence two.\n\nSecond paragraph sentence one."
        result = prepare_for_speech(text, lang="en")
        assert len(result.paragraphs) == 2

    def test_symbols_expanded_in_output(self):
        text = "Water boils at 100°C under normal pressure."
        result = prepare_for_speech(text, lang="en")
        all_text = " ".join(s for p in result.paragraphs for s in p)
        assert "degrees Celsius" in all_text

    def test_fig_refs_removed(self):
        text = "See (Fig 13.1) for a diagram of the process."
        result = prepare_for_speech(text, lang="en")
        all_text = " ".join(s for p in result.paragraphs for s in p)
        assert "Fig" not in all_text

    def test_empty_text(self):
        result = prepare_for_speech("", lang="en")
        assert result.paragraphs == []
        assert not result.truncated


# ===========================================================================
# Physics book real-world noise examples
# ===========================================================================

class TestPhysicsBookNoise:
    """Real-world noisy lines from a physics textbook PDF."""

    @pytest.mark.parametrize("line", [
        "RS",
        "ea",
        "@3 ",
        "| chapter",
        "|---|---|",
        ">>",
    ])
    def test_real_noise_filtered(self, line):
        text = f"Normal sentence before.\n{line}\nNormal sentence after."
        result = prepare_for_speech(text, lang="en")
        all_text = " ".join(s for p in result.paragraphs for s in p)
        assert line.strip() not in all_text

    @pytest.mark.parametrize("eq", [
        "ma=-kx",
        "KE. = 1/2 mv2",
    ])
    def test_real_equations_filtered(self, eq):
        text = f"Energy is described below.\n{eq}\nThis is the equation."
        result = prepare_for_speech(text, lang="en")
        all_text = " ".join(s for p in result.paragraphs for s in p)
        assert eq not in all_text

