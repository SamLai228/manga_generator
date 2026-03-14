"""
Generate multi-angle character views using Gemini Imagen API.
Creates front, 3/4, side, back views and expressions.
"""
import logging
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.gemini.client import generate_image
from models.character import CharacterMetadata

logger = logging.getLogger(__name__)

ANGLE_CONFIGS = {
    "front": "front view, facing directly forward, full body",
    "three_quarter": "three-quarter view, slight angle, full body",
    "side": "side profile view, facing left, full body",
    "back": "back view, facing away, full body",
}

EXPRESSION_CONFIGS = {
    "neutral": "neutral expression, calm face",
    "happy": "happy expression, smiling face",
}

CHARACTER_SHEET_PROMPT = """Character reference sheet for: {name}

Character description: {description}
Art style: {style}

{angle_desc}, {expression_desc}

manga character design, clean lineart, consistent character design, white background, professional manga art style"""

SHEET_COMPOSITE_PROMPT = """Character reference sheet for: {name}

Character appearance: {description}

Layout: a single image divided into a 2x2 grid with clear borders between cells.
- Top-left: front view, full body, facing directly forward, neutral expression
- Top-right: 3/4 view, full body, slight angle to the right, neutral expression
- Bottom-left: side profile, full body, facing left, neutral expression
- Bottom-right: back view, full body, facing away

Rules:
- All 4 views must show the same character with perfectly consistent design, colors, and markings
- White background in each cell
- Each cell is labeled with the view name (Front / 3/4 View / Side / Back)
- Clean character design lines

Art style (match exactly — including color palette, shading, and line style): {style}"""


def generate_character_angles(
    character: CharacterMetadata,
    output_dir: Path,
    angles: list[str] = None,
    expressions: list[str] = None,
) -> dict[str, Path]:
    """
    Generate multiple angle views for a character.

    Args:
        character: Character metadata with description and style
        output_dir: Directory to save generated images
        angles: List of angles to generate (default: all ANGLE_CONFIGS keys)
        expressions: List of expressions (default: ["neutral", "happy"])

    Returns:
        Dict mapping "{angle}_{expression}" -> Path
    """
    if angles is None:
        angles = list(ANGLE_CONFIGS.keys())
    if expressions is None:
        expressions = list(EXPRESSION_CONFIGS.keys())

    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    def generate_single(angle: str, expression: str) -> tuple[str, Path]:
        key = f"{angle}_{expression}"
        filename = f"{key}.png"
        output_path = output_dir / filename

        prompt = CHARACTER_SHEET_PROMPT.format(
            name=character.name,
            description=character.description,
            style=character.style_description or "manga style, clean lineart, full color",
            angle_desc=ANGLE_CONFIGS[angle],
            expression_desc=EXPRESSION_CONFIGS[expression],
        )

        try:
            generate_image(prompt=prompt, output_path=output_path)
            logger.info(f"Generated {key} for {character.name}")
            return key, output_path
        except Exception as e:
            logger.error(f"Failed to generate {key} for {character.name}: {e}")
            raise

    tasks = [(angle, expr) for angle in angles for expr in expressions]

    # Generate in parallel (up to 3 concurrent)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(generate_single, angle, expr): (angle, expr) for angle, expr in tasks}
        for future in as_completed(futures):
            try:
                key, path = future.result()
                results[key] = path
            except Exception as e:
                angle, expr = futures[future]
                logger.error(f"Generation failed for {angle}_{expr}: {e}")

    return results


def generate_character_sheet(
    character: CharacterMetadata,
    output_dir: Path,
    style_images: Optional[list[Path]] = None,
) -> Path:
    """
    Generate a single composite character reference sheet (all angles in one image).

    Returns:
        Path to the sheet image
    """
    output_path = output_dir / "sheet.png"
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt = SHEET_COMPOSITE_PROMPT.format(
        name=character.name,
        description=character.description,
        style=character.style_description or "manga style, clean lineart, full color",
    )

    generate_image(prompt=prompt, output_path=output_path, reference_images=style_images)
    logger.info(f"Generated character sheet for {character.name}")
    return output_path
