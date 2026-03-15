"""
Enrich panel scripts with character descriptions and style information
to create detailed image generation prompts.
"""
import logging
from typing import Optional

from models.manga import PanelScript, MangaScript
from models.character import CharacterIndexEntry
from services.manga_generator.character_retriever import get_character_prompt_description, get_character_sheet_image

logger = logging.getLogger(__name__)

PANEL_PROMPT_TEMPLATE = """manga panel, {camera}, {scene_desc}

Characters: {character_desc}

Action: {action}
Mood: {mood}
{dialogue_part}
Art style: {style}
{animal_note}
manga panel border, high quality manga art, black and white, clean lineart"""

HUMAN_SPECIES = {"human", "person", "man", "woman", "boy", "girl", "人"}

CAMERA_MAP = {
    "close-up": "extreme close-up shot, face and shoulders visible",
    "medium shot": "medium shot, character from waist up",
    "wide shot": "wide shot, full scene visible",
    "bird's eye": "bird's eye view, looking down",
    "worm's eye": "worm's eye view, looking up",
    "full body": "full body shot",
}


def enrich_panel(
    panel: PanelScript,
    character_entries: dict[str, Optional[CharacterIndexEntry]],
    global_style: str = "manga style, full color, clean lineart",
) -> str:
    """
    Generate an image generation prompt for a single panel.

    Args:
        panel: The panel script
        character_entries: Mapping of character name -> CharacterIndexEntry
        global_style: Art style description to apply globally

    Returns:
        Image generation prompt string
    """
    # Build character description
    char_descs = []
    has_animal = False
    for char_name in panel.characters:
        entry = character_entries.get(char_name)
        if entry:
            char_detail = get_character_prompt_description(entry.id)
            char_descs.append(f"{char_name}: {char_detail}")
            species = {s.lower() for s in (entry.tags.species or [])}
            if species and not species.intersection(HUMAN_SPECIES):
                has_animal = True
        else:
            char_descs.append(char_name)

    character_desc = "; ".join(char_descs) if char_descs else "no characters"

    # Map camera
    camera_desc = CAMERA_MAP.get(panel.camera.lower(), panel.camera)

    # Dialogue part
    dialogue_part = ""
    if panel.dialogue:
        dialogue_part = f'Dialogue bubble: "{panel.dialogue}"'

    # Animal restriction note
    animal_note = ""
    if has_animal:
        animal_note = "IMPORTANT: Characters are animals — do NOT draw any human-only actions (no hands in pockets, no pointing fingers, no thumbs up, no waving hands, no holding objects with hands). Use natural animal body language and postures only."

    prompt = PANEL_PROMPT_TEMPLATE.format(
        camera=camera_desc,
        scene_desc=panel.scene,
        character_desc=character_desc,
        action=panel.action,
        mood=panel.mood or "neutral",
        dialogue_part=dialogue_part,
        style=global_style,
        animal_note=animal_note,
    )

    return prompt.strip()


def build_page_prompt(
    script: MangaScript,
    character_entries: dict[str, Optional[CharacterIndexEntry]],
    global_style: str = "manga style, full color, clean lineart",
    style_reference_images: list = [],
) -> tuple[str, list]:
    """
    Build a single prompt for a 4-panel manga page image.

    Returns:
        (prompt string, list of reference image Paths for characters)
    """
    # Collect character descriptions, sheet images, and animal check
    all_char_descs = {}
    reference_images = []
    has_animal = False
    all_names = {name for panel in script.panels for name in panel.characters}
    for char_name in all_names:
        entry = character_entries.get(char_name)
        if entry:
            all_char_descs[char_name] = get_character_prompt_description(entry.id)
            species = {s.lower() for s in (entry.tags.species or [])}
            if species and not species.intersection(HUMAN_SPECIES):
                has_animal = True
            sheet = get_character_sheet_image(entry.id)
            if sheet:
                reference_images.append(sheet)
        else:
            all_char_descs[char_name] = char_name

    # Build per-panel descriptions
    panel_parts = []
    for panel in script.panels:
        camera_desc = CAMERA_MAP.get(panel.camera.lower(), panel.camera)
        part = f"Panel {panel.panel_number} ({camera_desc}): {panel.scene}. {panel.action}."
        if panel.dialogue:
            part += f' Speech bubble: "{panel.dialogue}"'
        panel_parts.append(part)

    animal_note = ""
    if has_animal:
        animal_note = "\nIMPORTANT: Characters are animals — do NOT draw human-only actions (no hands in pockets, no pointing fingers, no thumbs up, no waving hands). Use natural animal body language only."

    style_ref_note = ""
    if style_reference_images:
        n = len(style_reference_images)
        style_ref_note = f"\nIMPORTANT: The first {n} attached image(s) are art style references. Adopt their color palette, color scheme, line quality, shading style, and overall visual tone as the dominant aesthetic for the entire page. Prioritize these style images over any other visual references."
        reference_images = list(style_reference_images) + reference_images

    char_consistency_note = ""
    if any(img for img in reference_images if img not in style_reference_images):
        char_names = ", ".join(all_char_descs.keys())
        char_consistency_note = f"\nCRITICAL: The remaining attached image(s) show the character designs for {char_names}. Use them solely to identify each character's appearance — their markings, facial features, body shape, and character-specific colors. Do NOT use these character sheets to influence the overall art style or color palette of the page."

    characters_summary = "; ".join(
        f"{n}: {desc}" for n, desc in all_char_descs.items()
    ) or "no named characters"

    prompt = f"""4-panel manga page, 2x2 grid layout, each panel separated by borders.

Characters: {characters_summary}
{style_ref_note}{char_consistency_note}
{chr(10).join(panel_parts)}

Art style: {global_style}
{animal_note}
manga page, panel borders, high quality manga art, clean lineart"""

    return prompt.strip(), reference_images
