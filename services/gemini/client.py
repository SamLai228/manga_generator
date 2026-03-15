"""
Gemini API client wrapping google-genai SDK.
Supports text generation (gemini-2.0-flash) and image generation (imagen-3.0-generate-002).
"""
import base64
import io
import logging
from pathlib import Path
from typing import Optional

from google import genai as genai_new
from google.genai import types as genai_types

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Return configured Gemini client."""
    return genai_new.Client(api_key=settings.gemini_api_key)


def generate_text(prompt: str, system_instruction: str = "") -> str:
    """Generate text using Gemini text model."""
    client = _get_client()
    config = {}
    if system_instruction:
        config["system_instruction"] = system_instruction

    response = client.models.generate_content(
        model=settings.gemini_text_model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(**config) if config else None,
    )
    return response.text


def generate_text_with_images(prompt: str, image_paths: list[Path], system_instruction: str = "") -> str:
    """Generate text using Gemini with image inputs (Vision)."""
    client = _get_client()

    parts = []
    for img_path in image_paths:
        with open(img_path, "rb") as f:
            img_data = f.read()
        mime_type = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
        parts.append(genai_types.Part.from_bytes(data=img_data, mime_type=mime_type))
    parts.append(genai_types.Part.from_text(text=prompt))

    config = {}
    if system_instruction:
        config["system_instruction"] = system_instruction

    response = client.models.generate_content(
        model=settings.gemini_text_model,
        contents=parts,
        config=genai_types.GenerateContentConfig(**config) if config else None,
    )
    return response.text


def _extract_image_bytes_from_response(response) -> bytes:
    """Extract image bytes from a generate_content response."""
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return part.inline_data.data
    raise ValueError("No image found in response")


def generate_image(
    prompt: str,
    output_path: Path,
    reference_images: Optional[list[Path]] = None,
    aspect_ratio: str = "1:1",
) -> Path:
    """
    Generate an image using Gemini image model and save to output_path.
    Returns the path to the saved image.
    """
    client = _get_client()

    contents = []
    for img_path in (reference_images or []):
        if img_path.exists():
            with open(img_path, "rb") as f:
                ref_data = f.read()
            mime_type = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
            contents.append(genai_types.Part.from_bytes(data=ref_data, mime_type=mime_type))
    contents.append(genai_types.Part.from_text(text=prompt))

    response = client.models.generate_content(
        model=settings.gemini_image_model,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=genai_types.ImageConfig(aspect_ratio=aspect_ratio),
        ),
    )

    img_bytes = _extract_image_bytes_from_response(response)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_bytes)

    logger.info(f"Image saved to {output_path}")
    return output_path


def generate_image_bytes(prompt: str) -> bytes:
    """Generate an image and return raw bytes."""
    client = _get_client()
    response = client.models.generate_content(
        model=settings.gemini_image_model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )
    return _extract_image_bytes_from_response(response)
