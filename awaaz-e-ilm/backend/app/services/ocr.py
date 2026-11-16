"""OCR service for image-based documents.

Primary engine : Tesseract (eng + urd) via ``pytesseract``
Fallback engine: EasyOCR (en / ur)

Images are preprocessed with OpenCV before OCR:
  grayscale → denoise → deskew → adaptive threshold

Supported languages
-------------------
- ``"en"`` → Tesseract ``eng`` / EasyOCR ``en``
- ``"ur"`` → Tesseract ``urd`` / EasyOCR ``ur``
- ``"en+ur"`` → Tesseract ``eng+urd`` (EasyOCR runs both readers)
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tesseract executable path
# ---------------------------------------------------------------------------
# Resolution order:
#   1. TESSERACT_CMD env-var / Settings.tesseract_cmd  (explicit override)
#   2. Windows default: C:\Program Files\Tesseract-OCR\tesseract.exe
#   3. Leave unset → pytesseract searches PATH as usual

_WINDOWS_TESS_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _configure_tesseract() -> None:
    """Set pytesseract.pytesseract.tesseract_cmd from config / env / OS default."""
    try:
        import pytesseract
        from app.config import get_settings

        cmd = get_settings().tesseract_cmd.strip()
        if not cmd:
            # Auto-detect Windows default if not explicitly set
            if sys.platform == "win32" and os.path.isfile(_WINDOWS_TESS_DEFAULT):
                cmd = _WINDOWS_TESS_DEFAULT
                logger.debug("Tesseract: using Windows default path %s", cmd)

        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
    except Exception as exc:
        logger.debug("Tesseract path configuration skipped: %s", exc)


# Run once at module import time (lazy imports mean pytesseract may not be
# available yet, but _configure_tesseract() is also called inside
# run_tesseract() to handle deferred imports).
_configure_tesseract()

# ---------------------------------------------------------------------------
# Language-code mapping
# ---------------------------------------------------------------------------
_TESS_LANG_MAP = {"en": "eng", "ur": "urd", "en+ur": "eng+urd"}
_EASYOCR_LANG_MAP = {"en": ["en"], "ur": ["ur"], "en+ur": ["en", "ur"]}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OCRResult:
    """Result of an OCR run on a single image."""
    text: str
    engine: str  # "tesseract" or "easyocr"
    lang: str
    confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# Image preprocessing  (OpenCV)
# ---------------------------------------------------------------------------

def preprocess_image(
    image: np.ndarray,
    *,
    denoise: bool = True,
    deskew: bool = True,
    binarize: bool = True,
) -> np.ndarray:
    """Preprocess an image for better OCR accuracy.

    Pipeline:
        1. Convert to grayscale (if colour).
        2. De-noise with ``fastNlMeansDenoising``.
        3. Deskew by detecting the dominant text angle.
        4. Adaptive-threshold binarisation.

    Args:
        image:   Input image as a NumPy array (BGR or grayscale).
        denoise: Apply non-local means denoising.
        deskew:  Correct rotation / skew.
        binarize: Apply adaptive thresholding.

    Returns:
        Preprocessed grayscale image ready for OCR.
    """
    # 1. Grayscale
    if len(image.shape) == 3 and image.shape[2] >= 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 2. Denoise
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10)

    # 3. Deskew
    if deskew:
        gray = _deskew(gray)

    # 4. Binarize (adaptive threshold)
    if binarize:
        gray = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

    return gray


def _is_high_contrast(image: np.ndarray, threshold: float = 0.80) -> bool:
    """Return True when the image is already high-contrast (clean render).

    Uses Otsu's binarisation to estimate the white/black ratio.  If the
    image is overwhelmingly white-on-black (or black-on-white) text at
    good contrast, aggressive denoising and adaptive thresholding will
    do more harm than good.
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white_ratio = np.sum(binary == 255) / binary.size
    return white_ratio > threshold or white_ratio < (1 - threshold)


def smart_preprocess(
    image: np.ndarray,
    *,
    force: bool = False,
    binarize: bool = True,
) -> np.ndarray:
    """Conditionally preprocess: skip denoise+binarize for high-contrast images.

    For clean, digitally-rendered images the full pipeline (especially
    adaptive thresholding) can degrade multi-line Urdu OCR.  This wrapper
    detects high-contrast images and returns a simple grayscale conversion
    instead.

    Args:
        image:   Input image (BGR or grayscale).
        force:   Always run the full pipeline regardless of contrast.
        binarize: Whether to include binarization in the full pipeline.

    Returns:
        Preprocessed grayscale image.
    """
    if len(image.shape) == 3 and image.shape[2] >= 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if not force and _is_high_contrast(gray):
        logger.debug("High-contrast image detected — skipping aggressive preprocessing")
        return gray

    return preprocess_image(image, denoise=True, deskew=True, binarize=binarize)


def _deskew(image: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """Detect skew angle and rotate to correct it.

    Uses contour analysis to estimate the dominant text angle.
    Only corrects angles up to ±``max_angle`` degrees.
    """
    # Invert for contour detection
    inverted = cv2.bitwise_not(image)
    coords = np.column_stack(np.where(inverted > 0))

    if len(coords) < 100:
        return image  # not enough data to estimate angle

    angle = cv2.minAreaRect(coords)[-1]

    # cv2.minAreaRect returns angles in [-90, 0).  Normalise.
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) > max_angle or abs(angle) < 0.5:
        return image  # skip correction for extreme or negligible angles

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, rot_mat, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    logger.debug("Deskewed image by %.2f°", angle)
    return rotated


def load_image(path: str) -> np.ndarray:
    """Load an image from disk using OpenCV.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If the image cannot be decoded.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Image not found: {path}")
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not decode image: {path}")
    return img


# ---------------------------------------------------------------------------
# Tesseract OCR
# ---------------------------------------------------------------------------

def run_tesseract(
    image: np.ndarray,
    lang: str = "en",
    *,
    preprocess: bool = True,
) -> OCRResult:
    """Run Tesseract OCR on an image.

    Args:
        image:      Image as a NumPy array.
        lang:       Language code (``"en"``, ``"ur"``, ``"en+ur"``).
        preprocess: Whether to apply preprocessing first.

    Returns:
        An :class:`OCRResult`.

    Raises:
        RuntimeError: If Tesseract is not installed or the language pack
                      is missing.
    """
    import pytesseract

    # Ensure tesseract_cmd is configured (handles deferred module imports)
    _configure_tesseract()

    if preprocess:
        image = preprocess_image(image)

    tess_lang = _TESS_LANG_MAP.get(lang, "eng")

    try:
        text = pytesseract.image_to_string(image, lang=tess_lang)
        # Get confidence via image_to_data
        data = pytesseract.image_to_data(image, lang=tess_lang, output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in data["conf"] if int(c) > -1]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract is not installed. Install it with:\n"
            "  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-urd\n"
            "  macOS:         brew install tesseract\n"
            "  Windows:       https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except pytesseract.TesseractError as exc:
        raise RuntimeError(f"Tesseract error: {exc}")

    return OCRResult(
        text=text.strip(),
        engine="tesseract",
        lang=lang,
        confidence=avg_conf,
    )


# ---------------------------------------------------------------------------
# EasyOCR  (fallback)
# ---------------------------------------------------------------------------

# Lazy singleton — EasyOCR readers are heavy, so we cache them.
_easyocr_readers: dict[str, object] = {}


def _get_easyocr_reader(lang: str):
    """Get or create a cached EasyOCR reader for the given language.

    The model storage directory is taken from the ``EASYOCR_MODULE_PATH``
    environment variable if set (useful in sandboxed / test environments),
    otherwise EasyOCR uses its default ``~/.EasyOCR`` location.
    """
    import easyocr
    import tempfile

    key = lang
    if key not in _easyocr_readers:
        lang_list = _EASYOCR_LANG_MAP.get(lang, ["en"])

        # Allow redirecting the model cache to a writable directory
        model_dir = os.environ.get("EASYOCR_MODULE_PATH") or None
        if model_dir is None:
            # Fallback: use a temp dir if the default ~/.EasyOCR is not writable
            default_dir = os.path.join(os.path.expanduser("~"), ".EasyOCR")
            if not os.access(os.path.dirname(default_dir) or ".", os.W_OK):
                model_dir = os.path.join(tempfile.gettempdir(), "easyocr_cache")

        try:
            kwargs = {"gpu": False, "verbose": False}
            if model_dir:
                os.makedirs(model_dir, exist_ok=True)
                kwargs["model_storage_directory"] = model_dir
            _easyocr_readers[key] = easyocr.Reader(lang_list, **kwargs)
            logger.info("Created EasyOCR reader for %s (model_dir=%s)", lang_list, model_dir)
        except (PermissionError, OSError) as exc:
            raise RuntimeError(
                f"EasyOCR cannot create its model directory. "
                f"Set EASYOCR_MODULE_PATH to a writable path. Original error: {exc}"
            ) from exc

    return _easyocr_readers[key]


def run_easyocr(
    image: np.ndarray,
    lang: str = "en",
    *,
    preprocess: bool = True,
) -> OCRResult:
    """Run EasyOCR on an image (fallback engine).

    Args:
        image:      Image as a NumPy array.
        lang:       Language code (``"en"``, ``"ur"``, ``"en+ur"``).
        preprocess: Whether to apply preprocessing first.

    Returns:
        An :class:`OCRResult`.
    """
    if preprocess:
        image = preprocess_image(image, binarize=False)  # EasyOCR works better without binarisation

    reader = _get_easyocr_reader(lang)
    results = reader.readtext(image, detail=1)

    # Combine all text blocks
    text_parts = []
    confidences = []
    for bbox, text, conf in results:
        text_parts.append(text)
        confidences.append(conf)

    combined = " ".join(text_parts)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    return OCRResult(
        text=combined.strip(),
        engine="easyocr",
        lang=lang,
        confidence=avg_conf * 100,  # normalise to 0-100 like Tesseract
    )


# ---------------------------------------------------------------------------
# Public API — run_ocr with fallback
# ---------------------------------------------------------------------------

def run_ocr(
    image_or_path: str | np.ndarray,
    lang: str = "en",
    *,
    preprocess: bool = True,
    force_engine: Optional[str] = None,
) -> OCRResult:
    """Run OCR on an image with automatic fallback.

    Tries Tesseract first.  If Tesseract is unavailable or returns empty
    text, falls back to EasyOCR.

    Args:
        image_or_path: File path or NumPy image array.
        lang:          Language code (``"en"``, ``"ur"``, ``"en+ur"``).
        preprocess:    Apply image preprocessing.
        force_engine:  ``"tesseract"`` or ``"easyocr"`` to skip fallback.

    Returns:
        An :class:`OCRResult` from whichever engine succeeded.
    """
    # Load image if a path was given
    if isinstance(image_or_path, str):
        image = load_image(image_or_path)
    else:
        image = image_or_path

    # ── Try Tesseract ──────────────────────────────────────────────────────
    if force_engine != "easyocr":
        try:
            result = run_tesseract(image, lang, preprocess=preprocess)
            if result.text:
                logger.info(
                    "Tesseract (%s) extracted %d chars (conf=%.1f)",
                    lang, len(result.text), result.confidence or 0,
                )
                return result
            logger.warning("Tesseract returned empty text — falling back to EasyOCR")
        except RuntimeError as exc:
            logger.warning("Tesseract unavailable (%s) — falling back to EasyOCR", exc)

    if force_engine == "tesseract":
        # Caller explicitly asked for Tesseract only
        return OCRResult(text="", engine="tesseract", lang=lang, confidence=0.0)

    # ── Fallback: EasyOCR ──────────────────────────────────────────────────
    try:
        result = run_easyocr(image, lang, preprocess=preprocess)
        logger.info(
            "EasyOCR (%s) extracted %d chars (conf=%.1f)",
            lang, len(result.text), result.confidence or 0,
        )
        return result
    except Exception as exc:
        logger.error("EasyOCR also failed: %s", exc)
        return OCRResult(text="", engine="easyocr", lang=lang, confidence=0.0)
