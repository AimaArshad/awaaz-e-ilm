"""OCR evaluation script: generate 3 English + 3 Urdu fixtures with real font
shaping, then test Tesseract and EasyOCR each with and without OpenCV
preprocessing. Reports character-level accuracy in a Markdown table.

Font used: Segoe UI (C:\\Windows\\Fonts\\segoeui.ttf) — ships with Windows,
supports both Latin and Arabic/Urdu Unicode ranges, rendered via PIL with
HarfBuzz+FriBidi (raqm layout engine) for correct RTL shaping.

Usage:
    cd backend
    python ../scripts/evaluate_ocr.py

Requires: pytesseract (Tesseract installed), Pillow, opencv-python-headless,
          arabic-reshaper, python-bidi
Optional: easyocr (with downloaded models)
"""
from __future__ import annotations

import os
import sys
import re
import json
import textwrap
import tempfile
from dataclasses import dataclass
from typing import Optional

# ── Tesseract path ────────────────────────────────────────────────────────────
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
FIXTURES_DIR = os.path.join(PROJECT_ROOT, "backend", "tests", "fixtures")
EVAL_DIR     = os.path.join(FIXTURES_DIR, "eval")
GT_DIR       = os.path.join(FIXTURES_DIR, "ground_truth")
FONT_EN = r"C:\Windows\Fonts\times.ttf"       # Times New Roman — clean serif
FONT_UR = r"C:\Windows\Fonts\segoeui.ttf"     # Segoe UI — Arabic/Urdu support

os.makedirs(EVAL_DIR, exist_ok=True)
os.makedirs(GT_DIR, exist_ok=True)

# ── HarfBuzz / raqm check ─────────────────────────────────────────────────────
HAS_RAQM = features.check("raqm")
print(f"raqm (HarfBuzz+FriBidi): {HAS_RAQM}")


# =============================================================================
# Fixture definitions
# =============================================================================

ENGLISH_FIXTURES = [
    {
        "id": "en_short",
        "text": "The quick brown fox jumps over the lazy dog.",
        "font_size": 36,
        "desc": "English short — pangram, 36 px",
    },
    {
        "id": "en_medium",
        "text": (
            "Education is the most powerful weapon\n"
            "which you can use to change the world.\n"
            "— Nelson Mandela"
        ),
        "font_size": 32,
        "desc": "English medium — quote, multi-line, 32 px",
    },
    {
        "id": "en_long",
        "text": textwrap.fill(
            "Artificial intelligence is transforming every sector of society, "
            "from healthcare and education to transportation and entertainment. "
            "Machine learning models can now recognize speech, translate languages, "
            "diagnose diseases, and generate creative content with remarkable accuracy.",
            width=55,
        ),
        "font_size": 28,
        "desc": "English long — paragraph, 28 px",
    },
]

# For Urdu: PIL with raqm renders RTL correctly without needing arabic-reshaper.
# We pass language='ur', direction='rtl' to draw.text() when raqm is available.
URDU_FIXTURES = [
    {
        "id": "ur_short",
        "text": "یہ اردو زبان کا ایک ٹیسٹ ہے۔",
        "font_size": 40,
        "desc": "Urdu short — single sentence, 40 px",
    },
    {
        "id": "ur_medium",
        "text": "علم ایک ایسا خزانہ ہے جو کبھی ختم نہیں ہوتا۔\nتعلیم حاصل کرو، خواہ چین تک جانا پڑے۔",
        "font_size": 36,
        "desc": "Urdu medium — two sentences, 36 px",
    },
    {
        "id": "ur_long",
        "text": (
            "مصنوعی ذہانت آج کے دور کی سب سے بڑی تکنیکی پیشرفت ہے۔\n"
            "یہ طبی تشخیص، تعلیم، اور مواصلات میں انقلاب لا رہی ہے۔\n"
            "اردو زبان کو بھی اس ٹیکنالوجی سے فائدہ اٹھانا چاہیے۔"
        ),
        "font_size": 36,
        "line_spacing": 2.0,
        "desc": "Urdu long — paragraph, 36 px (wider line spacing for Tesseract)",
    },
]


# =============================================================================
# Image generation
# =============================================================================

def render_text_image(
    text: str,
    font_path: str,
    font_size: int,
    *,
    lang: str = "en",
    padding: int = 20,
    line_spacing: float = 1.4,
) -> Image.Image:
    """Render text to a white PIL image with correct shaping.

    For Urdu (lang='ur') uses PIL's raqm engine (HarfBuzz + FriBidi) for
    correct RTL ligature shaping when available. Falls back to arabic-reshaper
    + python-bidi as a compatibility path.
    """
    font = ImageFont.truetype(font_path, font_size)
    lines = text.splitlines() or [""]

    # Measure each line (use raqm layout params for Urdu so width is accurate)
    dummy = Image.new("RGB", (1, 1))
    dd = ImageDraw.Draw(dummy)
    line_sizes = []
    for line in lines:
        if lang == "ur" and HAS_RAQM:
            bbox = dd.textbbox((0, 0), line, font=font, language="ur", direction="rtl")
        else:
            bbox = dd.textbbox((0, 0), line, font=font)
        line_sizes.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))

    max_w = max(w for w, _ in line_sizes) if line_sizes else 100
    total_h = int(sum(h * line_spacing for _, h in line_sizes))
    img_w = max_w + 2 * padding
    img_h = total_h + 2 * padding

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    y = padding
    for line, (_, lh) in zip(lines, line_sizes):
        if lang == "ur":
            if HAS_RAQM:
                # PIL raqm: proper Urdu shaping via HarfBuzz
                # anchor='rt' = right-top; x = right edge of canvas
                draw.text(
                    (img_w - padding, y),
                    line,
                    font=font,
                    fill="black",
                    language="ur",
                    direction="rtl",
                    anchor="rt",
                )
            else:
                # Fallback: arabic-reshaper + python-bidi
                try:
                    import arabic_reshaper
                    from bidi.algorithm import get_display
                    shaped = get_display(arabic_reshaper.reshape(line))
                    bbox = draw.textbbox((0, 0), shaped, font=font)
                    x = img_w - padding - (bbox[2] - bbox[0])
                    draw.text((x, y), shaped, font=font, fill="black")
                except ImportError:
                    draw.text((padding, y), line, font=font, fill="black")
        else:
            draw.text((padding, y), line, font=font, fill="black")

        y += int(lh * line_spacing)

    return img


# =============================================================================
# OCR helpers
# =============================================================================

def preprocess(image: np.ndarray, *, denoise=True, deskew=True, binarize=True) -> np.ndarray:
    """OpenCV preprocessing pipeline from ocr.py."""
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))
    from app.services.ocr import preprocess_image
    return preprocess_image(image, denoise=denoise, deskew=deskew, binarize=binarize)


def _is_high_contrast(gray: np.ndarray, threshold: float = 0.80) -> bool:
    """Return True when the image is already high-contrast (clean render)."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white_ratio = np.sum(binary == 255) / binary.size
    return white_ratio > threshold or white_ratio < (1 - threshold)


def run_tess(gray: np.ndarray, lang_code: str) -> tuple[str, float]:
    tess_map = {"en": "eng", "ur": "urd"}
    tl = tess_map.get(lang_code, "eng")
    text = pytesseract.image_to_string(gray, lang=tl)
    data = pytesseract.image_to_data(gray, lang=tl, output_type=pytesseract.Output.DICT)
    confs = [int(c) for c in data["conf"] if int(c) > -1]
    conf = sum(confs) / len(confs) if confs else 0.0
    return text.strip(), conf


_EASYOCR_MODEL_DIR = os.environ.get("EASYOCR_MODULE_PATH") or os.path.join(
    os.path.expanduser("~"), ".EasyOCR", "model"
)
# Cached EasyOCR readers (heavy to initialise)
_easyocr_readers: dict[str, object] = {}


def run_easy(gray: np.ndarray, lang_code: str) -> Optional[tuple[str, float]]:
    """Run EasyOCR. Returns None only if models are genuinely missing."""
    try:
        import easyocr
        lang_map = {"en": ["en"], "ur": ["ur"], "en+ur": ["en", "ur"]}
        lang_list = lang_map.get(lang_code, ["en"])

        craft_path = os.path.join(_EASYOCR_MODEL_DIR, "craft_mlt_25k.pth")
        if not os.path.isfile(craft_path):
            print(f"    [EasyOCR] craft model not found at {craft_path}")
            return None

        key = lang_code
        if key not in _easyocr_readers:
            _easyocr_readers[key] = easyocr.Reader(
                lang_list, gpu=False, verbose=False,
                model_storage_directory=_EASYOCR_MODEL_DIR,
            )
        reader = _easyocr_readers[key]
        results = reader.readtext(gray, detail=1)
        texts = [t for _, t, _ in results]
        confs = [c for _, _, c in results]
        combined = " ".join(texts)
        avg_conf = (sum(confs) / len(confs) * 100) if confs else 0.0
        return combined.strip(), avg_conf
    except Exception as exc:
        print(f"    [EasyOCR] error: {exc}")
        return None


def char_accuracy(predicted: str, ground_truth: str) -> float:
    pred = re.sub(r"\s+", " ", predicted).strip()
    gt   = re.sub(r"\s+", " ", ground_truth).strip()
    if not gt:
        return 1.0 if not pred else 0.0
    try:
        from rapidfuzz.distance import Levenshtein
        distance = Levenshtein.distance(pred, gt)
    except ImportError:
        distance = sum(a != b for a, b in zip(pred.ljust(len(gt)), gt))
    return max(0.0, 1.0 - distance / max(len(gt), 1))


# =============================================================================
# Main evaluation
# =============================================================================

@dataclass
class EvalRow:
    fixture_id: str
    lang: str
    desc: str
    gt: str
    # Tesseract
    tess_no_pre_text: str = ""
    tess_no_pre_acc: float = 0.0
    tess_no_pre_conf: float = 0.0
    tess_pre_text: str = ""
    tess_pre_acc: float = 0.0
    tess_pre_conf: float = 0.0
    # EasyOCR
    easy_no_pre_text: str = ""
    easy_no_pre_acc: float = 0.0
    easy_no_pre_conf: float = 0.0
    easy_pre_text: str = ""
    easy_pre_acc: float = 0.0
    easy_pre_conf: float = 0.0
    easy_available: bool = False
    high_contrast: bool = False


def evaluate_fixture(fixture: dict, lang: str) -> EvalRow:
    fid   = fixture["id"]
    text  = fixture["text"]
    fsize = fixture["font_size"]
    desc  = fixture["desc"]
    line_spacing = fixture.get("line_spacing", 1.4)
    gt    = re.sub(r"\s+", " ", text).strip()

    # Save ground truth
    gt_path = os.path.join(GT_DIR, f"{fid}.txt")
    with open(gt_path, "w", encoding="utf-8") as f:
        f.write(text + "\n")

    # Choose font
    font_path = FONT_UR if lang == "ur" else FONT_EN

    # Render image
    img_pil = render_text_image(text, font_path, fsize, lang=lang, line_spacing=line_spacing)
    img_path = os.path.join(EVAL_DIR, f"{fid}.png")
    img_pil.save(img_path)

    # Load as OpenCV array
    bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    high_contrast = _is_high_contrast(gray)
    preprocessed  = preprocess(bgr, denoise=True, deskew=True, binarize=True)

    row = EvalRow(
        fixture_id=fid, lang=lang, desc=desc, gt=gt,
        high_contrast=high_contrast,
    )

    print(f"\n  [{fid}] {desc}  (high_contrast={high_contrast})")

    # ── Tesseract without preprocessing ──────────────────────────────────────
    t_text, t_conf = run_tess(gray, lang)
    row.tess_no_pre_text = t_text
    row.tess_no_pre_acc  = char_accuracy(t_text, gt)
    row.tess_no_pre_conf = t_conf
    print(f"    Tess no-pre  : acc={row.tess_no_pre_acc:.1%}  conf={t_conf:.1f}")

    # ── Tesseract with preprocessing ──────────────────────────────────────────
    t_text_p, t_conf_p = run_tess(preprocessed, lang)
    row.tess_pre_text = t_text_p
    row.tess_pre_acc  = char_accuracy(t_text_p, gt)
    row.tess_pre_conf = t_conf_p
    print(f"    Tess pre     : acc={row.tess_pre_acc:.1%}  conf={t_conf_p:.1f}")

    # ── EasyOCR without preprocessing ────────────────────────────────────────
    easy_result = run_easy(gray, lang)
    if easy_result is not None:
        row.easy_available = True
        e_text, e_conf = easy_result
        row.easy_no_pre_text = e_text
        row.easy_no_pre_acc  = char_accuracy(e_text, gt)
        row.easy_no_pre_conf = e_conf
        print(f"    Easy no-pre  : acc={row.easy_no_pre_acc:.1%}  conf={e_conf:.1f}")

        # ── EasyOCR with preprocessing (no binarization for EasyOCR) ─────────
        pre_easy = preprocess(bgr, denoise=True, deskew=True, binarize=False)
        easy_result_p = run_easy(pre_easy, lang)
        if easy_result_p is not None:
            e_text_p, e_conf_p = easy_result_p
            row.easy_pre_text = e_text_p
            row.easy_pre_acc  = char_accuracy(e_text_p, gt)
            row.easy_pre_conf = e_conf_p
            print(f"    Easy pre     : acc={row.easy_pre_acc:.1%}  conf={e_conf_p:.1f}")
    else:
        print(f"    EasyOCR      : not available (models not downloaded)")

    return row


def format_cell(acc: float, conf: float, available: bool = True) -> str:
    if not available:
        return "—"
    stars = "★" if acc >= 0.90 else ("▲" if acc >= 0.70 else "▼")
    return f"{acc:.1%} {stars} (conf {conf:.0f})"


def build_markdown_table(rows: list[EvalRow]) -> str:
    easy_any = any(r.easy_available for r in rows)
    if easy_any:
        header = (
            "| Fixture | Lang | Description | Tess no-pre | Tess + pre | Easy no-pre | Easy + pre | High-contrast? |\n"
            "|---------|------|-------------|-------------|------------|-------------|------------|----------------|\n"
        )
    else:
        header = (
            "| Fixture | Lang | Description | Tess no-pre | Tess + pre | High-contrast? |\n"
            "|---------|------|-------------|-------------|------------|----------------|\n"
        )

    lines = [header]
    for r in rows:
        tess_no = format_cell(r.tess_no_pre_acc, r.tess_no_pre_conf)
        tess_pr = format_cell(r.tess_pre_acc, r.tess_pre_conf)
        hc = "✓" if r.high_contrast else "✗"

        if easy_any:
            easy_no = format_cell(r.easy_no_pre_acc, r.easy_no_pre_conf, r.easy_available)
            easy_pr = format_cell(r.easy_pre_acc, r.easy_pre_conf, r.easy_available and bool(r.easy_pre_text))
            lines.append(
                f"| `{r.fixture_id}` | {r.lang.upper()} | {r.desc} | {tess_no} | {tess_pr} | {easy_no} | {easy_pr} | {hc} |\n"
            )
        else:
            lines.append(
                f"| `{r.fixture_id}` | {r.lang.upper()} | {r.desc} | {tess_no} | {tess_pr} | {hc} |\n"
            )
    return "".join(lines)


def main():
    rows: list[EvalRow] = []

    print("\n=== Evaluating English fixtures ===")
    for fx in ENGLISH_FIXTURES:
        rows.append(evaluate_fixture(fx, "en"))

    print("\n=== Evaluating Urdu fixtures ===")
    for fx in URDU_FIXTURES:
        rows.append(evaluate_fixture(fx, "ur"))

    table = build_markdown_table(rows)
    result_path = os.path.join(EVAL_DIR, "accuracy_results.md")
    with open(result_path, "w", encoding="utf-8") as f:
        f.write("# OCR Accuracy Evaluation\n\n")
        f.write(table)
        f.write("\n\nLegend: ★ ≥90%  ▲ 70–89%  ▼ <70%  conf=Tesseract confidence (0–100)\n")

    print(f"\n\nResults saved to: {result_path}")
    print("\n" + table)

    # Also output JSON for programmatic use
    json_path = os.path.join(EVAL_DIR, "accuracy_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([{
            "id": r.fixture_id, "lang": r.lang, "desc": r.desc,
            "tess_no_pre_acc": round(r.tess_no_pre_acc, 4),
            "tess_pre_acc":    round(r.tess_pre_acc, 4),
            "easy_no_pre_acc": round(r.easy_no_pre_acc, 4) if r.easy_available else None,
            "easy_pre_acc":    round(r.easy_pre_acc, 4) if r.easy_available else None,
            "high_contrast":   bool(r.high_contrast),  # numpy bool → Python bool
        } for r in rows], f, indent=2, ensure_ascii=False)

    return rows


if __name__ == "__main__":
    rows = main()
