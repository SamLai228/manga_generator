"""
Generate individual panel images using Gemini Imagen API.
Supports parallel generation.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from services.gemini.client import generate_image
from models.manga import PanelScript, MangaScript
from models.character import CharacterIndexEntry
from services.manga_generator.panel_enricher import enrich_panel
from services.manga_generator.character_retriever import (
    retrieve_characters_for_script,
    get_best_angle_image,
)

logger = logging.getLogger(__name__)


def generate_panel(
    panel: PanelScript,
    character_entries: dict[str, Optional[CharacterIndexEntry]],
    output_path: Path,
    style: str = "manga style, full color, clean lineart",
) -> Path:
    """
    Generate a single manga panel image.

    Returns:
        Path to generated image
    """
    prompt = enrich_panel(panel, character_entries, global_style=style)
    logger.info(f"Generating panel {panel.panel_number}: {prompt[:80]}...")

    # Find a reference image if available (use first character's front view)
    reference_image = None
    for char_name in panel.characters:
        entry = character_entries.get(char_name)
        if entry:
            ref = get_best_angle_image(entry.id, preferred_angle="front")
            if ref:
                reference_image = ref
                break

    generate_image(
        prompt=prompt,
        output_path=output_path,
        reference_images=[reference_image] if reference_image else None,
    )
    return output_path


def generate_all_panels(
    script: MangaScript,
    output_dir: Path,
    style: str = "manga style, full color, clean lineart",
    max_workers: int = 2,
) -> list[Path]:
    """
    Generate all 4 panels, potentially in parallel.

    Args:
        script: The manga script with 4 panels
        output_dir: Directory to save panel images
        style: Art style string
        max_workers: Max parallel image generations

    Returns:
        List of 4 panel image paths (in order)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect all character names
    all_character_names = []
    for panel in script.panels:
        all_character_names.extend(panel.characters)

    # Retrieve character data
    character_entries = retrieve_characters_for_script(all_character_names)

    # Map panel_number -> output path
    panel_paths = {
        p.panel_number: output_dir / f"panel_{p.panel_number}.png"
        for p in script.panels
    }

    results = {}

    def generate_one(panel: PanelScript) -> tuple[int, Path]:
        path = panel_paths[panel.panel_number]
        result_path = generate_panel(
            panel=panel,
            character_entries=character_entries,
            output_path=path,
            style=style,
        )
        return panel.panel_number, result_path

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(generate_one, panel): panel for panel in script.panels}
        for future in as_completed(futures):
            try:
                panel_num, path = future.result()
                results[panel_num] = path
                logger.info(f"Panel {panel_num} generated: {path}")
            except Exception as e:
                panel = futures[future]
                logger.error(f"Panel {panel.panel_number} generation failed: {e}")
                raise

    # Return in order
    return [results[i] for i in sorted(results.keys())]
