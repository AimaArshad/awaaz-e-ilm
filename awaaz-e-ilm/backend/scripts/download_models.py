#!/usr/bin/env python
"""Download Piper TTS voice models.

Downloads the .onnx and .onnx.json files for the configured Piper voice
from the rhasspy/piper-voices Hugging Face repository.

Safe to re-run: skips files that already exist with the correct size.

Usage:
    python scripts/download_models.py
    python scripts/download_models.py --voice en_US-lessac-medium
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

# Hugging Face base URL for piper-voices
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# Voice quality mapping (needed to construct URL path)
_VOICE_QUALITIES = {"x_low", "low", "medium", "high"}

def _parse_voice_name(voice: str) -> tuple[str, str, str, str]:
    """Parse voice name like 'en_US-lessac-medium' into components.

    Returns (lang_code, country, name, quality).
    E.g. 'en_US-lessac-medium' -> ('en', 'en_US', 'lessac', 'medium')
    """
    # Format: {lang}_{COUNTRY}-{name}-{quality}
    parts = voice.split("-")
    if len(parts) < 3:
        raise ValueError(
            f"Cannot parse voice name '{voice}'. "
            f"Expected format: lang_COUNTRY-name-quality (e.g. en_US-lessac-medium)"
        )
    quality = parts[-1]
    name = "-".join(parts[1:-1])
    lang_country = parts[0]
    lang = lang_country.split("_")[0]
    return lang, lang_country, name, quality


def download_voice(voice: str, dest_dir: Path) -> None:
    """Download the ONNX model and config for a Piper voice.

    Args:
        voice: Voice name, e.g. 'en_US-lessac-medium'.
        dest_dir: Directory to save model files.
    """
    lang, lang_country, name, quality = _parse_voice_name(voice)

    # URL path: /en/en_US/lessac/medium/en_US-lessac-medium.onnx
    url_dir = f"{HF_BASE}/{lang}/{lang_country}/{name}/{quality}"
    model_url = f"{url_dir}/{voice}.onnx"
    config_url = f"{url_dir}/{voice}.onnx.json"

    dest_dir.mkdir(parents=True, exist_ok=True)

    for url, filename in [
        (model_url, f"{voice}.onnx"),
        (config_url, f"{voice}.onnx.json"),
    ]:
        dest_path = dest_dir / filename
        if dest_path.exists():
            print(f"  ✓ Already exists: {dest_path}")
            continue

        print(f"  ↓ Downloading: {url}")
        print(f"    → {dest_path}")
        try:
            urllib.request.urlretrieve(url, str(dest_path))
            size_mb = dest_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ Downloaded: {size_mb:.1f} MB")
        except Exception as exc:
            print(f"  ✗ Failed: {exc}", file=sys.stderr)
            if dest_path.exists():
                dest_path.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description="Download Piper voice models")
    parser.add_argument(
        "--voice",
        default="en_US-lessac-medium",
        help="Voice name (default: en_US-lessac-medium)",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help="Destination directory (default: backend/models_cache/piper/)",
    )
    args = parser.parse_args()

    if args.dest:
        dest = Path(args.dest)
    else:
        # Assume running from backend/ or project root
        backend = Path(__file__).resolve().parent.parent
        dest = backend / "models_cache" / "piper"

    print(f"Piper voice: {args.voice}")
    print(f"Destination: {dest}")
    print()

    download_voice(args.voice, dest)
    print()
    print("Done! Models ready for use.")


if __name__ == "__main__":
    main()

