"""
Analyze character features from reference images and generate tag suggestions.
Uses Gemini Vision to extract character traits and suggest structured tags.
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional

from services.gemini.client import generate_text_with_images, generate_text
from models.character import CharacterTags

logger = logging.getLogger(__name__)

CHARACTER_ANALYSIS_PROMPT = """Analyze this character image and extract detailed information about the character.

Return a JSON object with the following structure:
{
  "description": "A 2-3 sentence visual description of the character",
  "tags": {
    "species": ["human", "elf", "cat", etc - list species/race],
    "hair": ["color", "length", "style" - e.g. "black", "short", "spiky"],
    "clothing": ["item_type", "color" - e.g. "school_uniform", "blue", "jacket"],
    "role": ["protagonist", "antagonist", "student", "teacher", etc],
    "personality": ["cheerful", "serious", "clumsy", etc - infer from appearance/expression],
    "custom": ["any other distinctive features like glasses, scars, accessories"]
  }
}

Be specific and use lowercase snake_case for multi-word tags. Return ONLY the JSON, no other text."""

CHARACTER_ANALYSIS_TEXT_PROMPT = """Based on this character description, suggest appropriate tags for a character database.

Character description: {description}

Return a JSON object:
{{
  "description": "refined description",
  "tags": {{
    "species": [],
    "hair": [],
    "clothing": [],
    "role": [],
    "personality": [],
    "custom": []
  }}
}}

Return ONLY the JSON, no other text."""


def analyze_character_from_images(
    image_paths: list[Path],
    name: str = "",
    additional_description: str = "",
) -> tuple[str, CharacterTags]:
    """
    Analyze character from reference images.

    Returns:
        Tuple of (description string, CharacterTags)
    """
    valid_paths = [p for p in image_paths if p.exists()]

    if valid_paths:
        prompt = CHARACTER_ANALYSIS_PROMPT
        if additional_description:
            prompt += f"\n\nAdditional context about this character: {additional_description}"
        if name:
            prompt += f"\nCharacter name: {name}"

        try:
            raw = generate_text_with_images(prompt=prompt, image_paths=valid_paths[:5])
            return _parse_analysis_response(raw, name)
        except Exception as e:
            logger.error(f"Character analysis from images failed: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                raise

    # Fallback: text-only analysis if we have a description
    if additional_description:
        try:
            prompt = CHARACTER_ANALYSIS_TEXT_PROMPT.format(description=additional_description)
            raw = generate_text(prompt)
            return _parse_analysis_response(raw, name)
        except Exception as e:
            logger.error(f"Character analysis from text failed: {e}")
            raise

    # Default fallback (no images, no description)
    description = f"Character named {name}" if name else "Unknown character"
    return description, CharacterTags()


def _parse_analysis_response(raw: str, name: str = "") -> tuple[str, CharacterTags]:
    """Parse Gemini response into description and tags."""
    # Try to extract JSON from response
    raw = raw.strip()

    # Remove markdown code blocks if present
    if "```json" in raw:
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
    elif "```" in raw:
        raw = re.sub(r"```\s*", "", raw)

    raw = raw.strip()

    try:
        data = json.loads(raw)
        description = data.get("description", f"Character {name}")
        tags_data = data.get("tags", {})
        tags = CharacterTags(
            species=tags_data.get("species", []),
            hair=tags_data.get("hair", []),
            clothing=tags_data.get("clothing", []),
            role=tags_data.get("role", []),
            personality=tags_data.get("personality", []),
            custom=tags_data.get("custom", []),
        )
        return description, tags
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse character analysis JSON: {e}\nRaw: {raw[:200]}")
        return f"Character {name}", CharacterTags()
