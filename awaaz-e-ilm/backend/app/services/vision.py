"""Vision / image captioning service.

Milestone 2 implementation plan
--------------------------------
Uses Florence-2 (microsoft/Florence-2-base) to generate alt-text captions
for images embedded in documents, making them accessible to visually impaired
readers via TTS.

Pipeline
--------
1. Load model once at startup into a module-level singleton.
2. For each image region: `caption_image(pil_image)` → caption string.
3. Inject caption into the chapter text: "[Image: <caption>]".
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image


async def caption_image(image: "Image") -> str:
    """Generate an accessibility caption for an embedded image.

    Args:
        image: A PIL Image object.

    Returns:
        Human-readable caption string (English).

    TODO (Milestone 2):
        - Load `AutoProcessor` and `AutoModelForCausalLM` from HuggingFace.
        - Run Florence-2 `<CAPTION>` task.
        - Cache the model using `functools.lru_cache` or a module singleton.
    """
    raise NotImplementedError("Image captioning coming in Milestone 2.")
