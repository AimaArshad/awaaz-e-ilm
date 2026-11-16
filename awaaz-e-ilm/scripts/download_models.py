#!/usr/bin/env python3
"""Download and cache all required AI models for Awaaz-e-Ilm.

Usage:
    python scripts/download_models.py [--models-dir ./backend/models_cache]

This script uses huggingface_hub to download model weights into the
configured models cache directory. Run this once before starting the server
in an environment with internet access; subsequent runs use the local cache.

Models downloaded
-----------------
- openai/whisper-small          (STT)
- microsoft/Florence-2-base     (image captioning)
- Helsinki-NLP/opus-mt-en-ur    (translation EN→UR)
- Helsinki-NLP/opus-mt-ur-en    (translation UR→EN)
- facebook/mms-tts-urd          (Urdu TTS)
- hexgrad/Kokoro-82M            (English TTS)
"""
import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Awaaz-e-Ilm AI models")
    parser.add_argument(
        "--models-dir",
        default=os.environ.get("MODELS_CACHE_DIR", "./backend/models_cache"),
        help="Directory to cache downloaded models",
    )
    parser.add_argument(
        "--skip-tts", action="store_true", help="Skip TTS model downloads"
    )
    parser.add_argument(
        "--skip-translation", action="store_true", help="Skip translation model downloads"
    )
    return parser.parse_args()


def download_model(repo_id: str, cache_dir: str, model_type: str = "model") -> None:
    """Download a HuggingFace model/dataset into the cache directory."""
    try:
        from huggingface_hub import snapshot_download

        print(f"⬇  Downloading {repo_id} → {cache_dir}/{repo_id.replace('/', '--')} …")
        snapshot_download(
            repo_id=repo_id,
            cache_dir=cache_dir,
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
        )
        print(f"   ✅ {repo_id}")
    except Exception as exc:
        print(f"   ❌ Failed to download {repo_id}: {exc}", file=sys.stderr)


def main() -> None:
    args = parse_args()
    cache_dir = str(Path(args.models_dir).resolve())
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n📦 Awaaz-e-Ilm Model Downloader")
    print(f"   Cache directory: {cache_dir}\n")

    # Check huggingface_hub is installed
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        print("❌ huggingface_hub not installed. Run: pip install huggingface_hub", file=sys.stderr)
        sys.exit(1)

    # ── STT ──────────────────────────────────────────────────────────────────
    print("── Speech-to-Text (Whisper) ──")
    download_model("openai/whisper-small", cache_dir)

    # ── Vision ───────────────────────────────────────────────────────────────
    print("\n── Vision / Image Captioning ──")
    download_model("microsoft/Florence-2-base", cache_dir)

    # ── Translation ──────────────────────────────────────────────────────────
    if not args.skip_translation:
        print("\n── Translation ──")
        download_model("Helsinki-NLP/opus-mt-en-ur", cache_dir)
        download_model("Helsinki-NLP/opus-mt-ur-en", cache_dir)

    # ── TTS ──────────────────────────────────────────────────────────────────
    if not args.skip_tts:
        print("\n── Text-to-Speech ──")
        download_model("hexgrad/Kokoro-82M", cache_dir)
        download_model("facebook/mms-tts-urd", cache_dir)

    print("\n✅ All downloads complete.")
    print(f"   Set MODELS_CACHE_DIR={cache_dir} in your .env file.\n")


if __name__ == "__main__":
    main()
