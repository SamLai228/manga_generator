"""
Character registry: orchestrates character creation and local storage.
"""
import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.character import CharacterMetadata, CharacterTags, CharacterIndexEntry
from services.character_studio.style_extractor import extract_style_from_images
from services.character_studio.character_analyzer import analyze_character_from_images
from services.character_studio.multi_angle_generator import generate_character_sheet
from services.retrieval.tag_store import add_character, resolve_unique_name
from config.settings import settings

logger = logging.getLogger(__name__)


def register_character(
    name: str,
    reference_images: list[Path],
    style_images: Optional[list[Path]] = None,
    additional_description: str = "",
    confirmed_tags: Optional[CharacterTags] = None,
    generate_angles: bool = True,
) -> CharacterMetadata:
    """
    Full character registration pipeline:
    1. Extract style from reference images
    2. Analyze character and suggest tags
    3. Generate multi-angle views
    4. Save to local filesystem and update index

    Args:
        name: Character name
        reference_images: Paths to reference images
        additional_description: User-provided description
        confirmed_tags: Pre-confirmed tags (skips AI suggestion if provided)
        generate_angles: Whether to generate multi-angle views

    Returns:
        CharacterMetadata for the registered character
    """
    name = resolve_unique_name(name)
    character_id = str(uuid.uuid4())[:8]
    char_dir = settings.characters_dir / character_id
    char_dir.mkdir(parents=True, exist_ok=True)

    # Copy reference images to character directory
    saved_ref_paths = []
    for i, ref_path in enumerate(reference_images):
        if ref_path.exists():
            dest = char_dir / f"reference_{i}{ref_path.suffix}"
            shutil.copy2(ref_path, dest)
            saved_ref_paths.append(dest)

    # Step 1: Extract style (prefer dedicated style images, fallback to photos)
    logger.info(f"Extracting style for {name}...")
    style_source = style_images if style_images else saved_ref_paths
    style_description = extract_style_from_images(style_source)

    # Step 2: Analyze character
    logger.info(f"Analyzing character {name}...")
    description, suggested_tags = analyze_character_from_images(
        image_paths=saved_ref_paths,
        name=name,
        additional_description=additional_description,
    )

    # Use confirmed tags if provided, otherwise use AI suggestions
    final_tags = confirmed_tags if confirmed_tags else suggested_tags

    # Create character metadata
    character = CharacterMetadata(
        id=character_id,
        name=name,
        description=description,
        style_description=style_description,
        tags=final_tags,
        angles=[],
        created_at=datetime.utcnow(),
        reference_images=[str(p) for p in saved_ref_paths],
    )

    # Step 3: Generate single multi-angle sheet
    sheet_path = None
    if generate_angles:
        logger.info(f"Generating multi-angle sheet for {name}...")
        try:
            sheet_path = generate_character_sheet(character=character, output_dir=char_dir, style_images=style_images)
            character.angles = ["sheet.png"]
        except Exception as e:
            logger.error(f"Sheet generation failed for {name}: {e}")

    # Step 4: Save metadata
    meta_path = char_dir / "character.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(character.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    # Step 5: Update index
    index_entry = CharacterIndexEntry(
        id=character_id,
        name=name,
        tags=final_tags,
        description=description,
        style_description=style_description,
        sheet_path=str(char_dir / "sheet.png") if sheet_path else "",
    )
    add_character(index_entry)

    logger.info(f"Character '{name}' registered with ID {character_id}")
    return character


def duplicate_character(character_id: str) -> Optional[CharacterMetadata]:
    """Duplicate an existing character, creating a copy with a new ID."""
    original = get_character_metadata(character_id)
    if not original:
        return None

    new_id = str(uuid.uuid4())[:8]
    original_dir = settings.characters_dir / character_id
    new_dir = settings.characters_dir / new_id

    shutil.copytree(original_dir, new_dir)

    # Update reference_images paths
    new_ref_images = [p.replace(character_id, new_id) for p in original.reference_images]

    new_character = CharacterMetadata(
        id=new_id,
        name=f"{original.name} 副本",
        description=original.description,
        style_description=original.style_description,
        tags=original.tags,
        angles=original.angles,
        created_at=datetime.utcnow(),
        reference_images=new_ref_images,
    )

    meta_path = new_dir / "character.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(new_character.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    index_entry = CharacterIndexEntry(
        id=new_id,
        name=new_character.name,
        tags=new_character.tags,
        description=new_character.description,
        style_description=new_character.style_description,
        sheet_path=str(new_dir / "sheet.png") if (new_dir / "sheet.png").exists() else "",
    )
    add_character(index_entry)

    logger.info(f"Character '{original.name}' duplicated as '{new_character.name}' with ID {new_id}")
    return new_character


def get_character_metadata(character_id: str) -> Optional[CharacterMetadata]:
    """Load character metadata from local filesystem."""
    char_dir = settings.characters_dir / character_id
    meta_path = char_dir / "character.json"
    if not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CharacterMetadata(**data)


def update_character_name(character_id: str, name: str) -> Optional[CharacterMetadata]:
    """Update the name of an existing character."""
    character = get_character_metadata(character_id)
    if not character:
        return None

    character.name = name
    char_dir = settings.characters_dir / character_id
    meta_path = char_dir / "character.json"

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(character.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    # Update index entry
    index_entry = CharacterIndexEntry(
        id=character_id,
        name=name,
        tags=character.tags,
        description=character.description,
        style_description=character.style_description,
        sheet_path=str(char_dir / "sheet.png") if (char_dir / "sheet.png").exists() else "",
    )
    add_character(index_entry)

    return character


def update_character_tags(character_id: str, tags: CharacterTags) -> Optional[CharacterMetadata]:
    """Update tags for an existing character."""
    character = get_character_metadata(character_id)
    if not character:
        return None

    character.tags = tags
    char_dir = settings.characters_dir / character_id
    meta_path = char_dir / "character.json"

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(character.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    # Update index entry
    index_entry = CharacterIndexEntry(
        id=character_id,
        name=character.name,
        tags=tags,
        description=character.description,
        style_description=character.style_description,
        sheet_path=str(char_dir / "sheet.png") if (char_dir / "sheet.png").exists() else "",
    )
    add_character(index_entry)

    return character
