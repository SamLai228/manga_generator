"""
Retrieve character data for manga panels based on character names in script.
"""
import logging
from pathlib import Path
from typing import Optional

from models.character import CharacterIndexEntry, CharacterMetadata
from services.retrieval.tag_store import get_character_by_name, search_characters
from services.character_studio.character_registry import get_character_metadata
from config.settings import settings

logger = logging.getLogger(__name__)


def retrieve_characters_for_script(
    character_names: list[str],
) -> dict[str, Optional[CharacterIndexEntry]]:
    """
    Retrieve character index entries for all characters mentioned in a script.

    Args:
        character_names: List of character names from the manga script

    Returns:
        Dict mapping character_name -> CharacterIndexEntry (or None if not found)
    """
    results = {}
    for name in set(character_names):  # deduplicate
        entry = get_character_by_name(name)
        if entry:
            logger.info(f"Found character '{name}' in index (id={entry.id})")
        else:
            logger.warning(f"Character '{name}' not found in index")
        results[name] = entry
    return results


def get_best_angle_image(
    character_id: str,
    preferred_angle: str = "front",
    expression: str = "neutral",
) -> Optional[Path]:
    """
    Get the best matching angle image for a character.

    Args:
        character_id: The character's ID
        preferred_angle: Preferred view angle (front, three_quarter, side, back)
        expression: Preferred expression (neutral, happy)

    Returns:
        Path to the best matching image, or None
    """
    char_dir = settings.characters_dir / character_id
    if not char_dir.exists():
        return None

    # Try exact match first
    exact = char_dir / f"{preferred_angle}_{expression}.png"
    if exact.exists():
        return exact

    # Try alternate expression
    alt_expr = "happy" if expression == "neutral" else "neutral"
    alt = char_dir / f"{preferred_angle}_{alt_expr}.png"
    if alt.exists():
        return alt

    # Try alternate angles
    angle_fallbacks = ["front", "three_quarter", "side", "back"]
    for angle in angle_fallbacks:
        for expr in [expression, alt_expr]:
            path = char_dir / f"{angle}_{expr}.png"
            if path.exists():
                return path

    # Fall back to sheet
    sheet = char_dir / "sheet.png"
    if sheet.exists():
        return sheet

    # Try any reference image
    for ref in char_dir.glob("reference_*"):
        return ref

    return None


def get_character_sheet_image(character_id: str) -> Optional[Path]:
    """
    Return the sheet.png for a character, or best available reference image.
    """
    char_dir = settings.characters_dir / character_id
    sheet = char_dir / "sheet.png"
    if sheet.exists():
        return sheet
    for ref in char_dir.glob("reference_*"):
        return ref
    return None


def get_character_prompt_description(character_id: str) -> str:
    """
    Get a prompt-ready description of a character for image generation.

    Returns:
        String description combining character metadata and tags
    """
    metadata = get_character_metadata(character_id)
    if not metadata:
        return ""

    tag_parts = []
    tags = metadata.tags
    if tags.hair:
        tag_parts.append(f"hair: {', '.join(tags.hair)}")
    if tags.clothing:
        tag_parts.append(f"wearing: {', '.join(tags.clothing)}")
    if tags.species:
        tag_parts.append(f"species: {', '.join(tags.species)}")
    if tags.custom:
        tag_parts.append(", ".join(tags.custom))

    tag_str = "; ".join(tag_parts)
    return f"{metadata.description}. {tag_str}".strip(". ")
