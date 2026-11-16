"""File system utility helpers.

Provides consistent path construction for the storage directory tree and
ensures directories exist before writing files.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def get_storage_path(*parts: str) -> str:
    """Build an absolute path under the configured STORAGE_DIR.

    Args:
        *parts: Path components to join under STORAGE_DIR.

    Returns:
        Absolute path string.

    Example:
        >>> get_storage_path("uploads", "42", "book.pdf")
        '/app/storage/uploads/42/book.pdf'
    """
    return os.path.join(settings.storage_dir, *parts)


def get_models_path(*parts: str) -> str:
    """Build an absolute path under the configured MODELS_CACHE_DIR.

    Args:
        *parts: Path components to join under MODELS_CACHE_DIR.

    Returns:
        Absolute path string.
    """
    return os.path.join(settings.models_cache_dir, *parts)


def ensure_dir(path: str) -> str:
    """Create a directory (and all parents) if it does not exist.

    Args:
        path: Directory path to create.

    Returns:
        The same path, for chaining convenience.
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(name: str, max_length: int = 128) -> str:
    """Sanitise a filename by removing unsafe characters.

    Args:
        name: Original filename.
        max_length: Maximum length of the returned filename.

    Returns:
        Sanitised filename string.
    """
    # Keep only alphanumeric, dots, hyphens, underscores
    import re
    safe = re.sub(r"[^\w.\-]", "_", name)
    return safe[:max_length]
