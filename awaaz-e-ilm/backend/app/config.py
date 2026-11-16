"""Application configuration loaded from environment variables / .env file.

Uses pydantic-settings for type-safe, validated configuration.
All settings can be overridden via environment variables.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ──────────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key"
    debug: bool = True

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./awaaz.db"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_dir: str = "./storage"
    models_cache_dir: str = "./models_cache"

    # ── Device ────────────────────────────────────────────────────────────────
    device: str = "auto"

    # ── Models ────────────────────────────────────────────────────────────────
    whisper_model: str = "small"
    image_caption_model: str = "microsoft/Florence-2-base"
    translation_en_ur_model: str = "Helsinki-NLP/opus-mt-en-ur"
    translation_ur_en_model: str = "Helsinki-NLP/opus-mt-ur-en"

    # ── OCR ───────────────────────────────────────────────────────────────────
    # Path to the tesseract executable.  Auto-detected on Windows if unset.
    tesseract_cmd: str = ""

    # ── TTS ───────────────────────────────────────────────────────────────────
    tts_en_engine: str = "piper"
    tts_ur_engine: str = "mms"
    enable_edge_tts: bool = False
    piper_voice: str = "en_US-lessac-medium"
    audio_max_chars: int = 8000


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
