"""
Extract art style description from reference images using Gemini Vision.
"""
import logging
from pathlib import Path

from services.gemini.client import generate_text_with_images, generate_text

logger = logging.getLogger(__name__)

STYLE_EXTRACTION_PROMPT = """Analyze the art style of this character image and provide a concise description suitable for use as an image generation prompt.

Focus on:
- Overall art style (e.g., anime, manga, western comic, realistic, chibi)
- Line art characteristics (clean lines, sketchy, bold outlines)
- Coloring style (black and white, flat colors, cel shading, watercolor)
- Shading technique
- Any distinctive visual elements

Respond with a single paragraph of 2-4 sentences that could be appended to an image generation prompt to replicate this style. Be specific and technical."""


def extract_style_from_images(image_paths: list[Path]) -> str:
    """
    Analyze reference images and return a style description string.

    Args:
        image_paths: List of paths to reference images

    Returns:
        Style description string suitable for prompt injection
    """
    if not image_paths:
        return "manga style, black and white, clean lineart, detailed"

    valid_paths = [p for p in image_paths if p.exists()]
    if not valid_paths:
        logger.warning("No valid image paths provided for style extraction")
        return "manga style, black and white, clean lineart, detailed"

    try:
        style_desc = generate_text_with_images(
            prompt=STYLE_EXTRACTION_PROMPT,
            image_paths=valid_paths[:3],  # max 3 reference images for style
        )
        logger.info(f"Extracted style: {style_desc[:100]}...")
        return style_desc.strip()
    except Exception as e:
        logger.error(f"Style extraction failed: {e}")
        return "manga style, black and white, clean lineart, detailed"
