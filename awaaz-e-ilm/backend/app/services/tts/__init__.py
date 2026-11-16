"""TTS sub-package.

Importing this package registers all available TTS engines in the registry.
Use ``from app.services.tts.base import get_engine`` to obtain an engine.
"""
# Register engines by importing their modules (each calls register_engine)
from app.services.tts import piper_en  # noqa: F401
