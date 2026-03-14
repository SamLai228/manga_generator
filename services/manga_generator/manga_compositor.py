"""
Compose 4 manga panels into a single manga page using PIL.
Handles layout, borders, dialogue boxes, and font rendering.
"""
import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from models.manga import MangaScript

logger = logging.getLogger(__name__)

# Layout constants
PAGE_WIDTH = 800
PAGE_HEIGHT = 1100
MARGIN = 20
PANEL_BORDER = 3
PANEL_GAP = 10

# Dialogue bubble constants
BUBBLE_PADDING = 8
BUBBLE_RADIUS = 15
FONT_SIZE = 16
TITLE_FONT_SIZE = 24


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a CJK-compatible font."""
    font_candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS Chinese
        "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "assets/fonts/NotoSansCJK-Regular.ttc",
    ]
    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _draw_dialogue_bubble(
    draw: ImageDraw.Draw,
    text: str,
    center_x: int,
    center_y: int,
    font: ImageFont.FreeTypeFont,
    max_width: int = 200,
) -> None:
    """Draw an oval dialogue bubble with text."""
    if not text:
        return

    # Calculate text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    bubble_w = min(text_w + BUBBLE_PADDING * 4, max_width)
    bubble_h = text_h + BUBBLE_PADDING * 2

    x0 = center_x - bubble_w // 2
    y0 = center_y - bubble_h // 2
    x1 = center_x + bubble_w // 2
    y1 = center_y + bubble_h // 2

    # Draw bubble (white fill, black border)
    draw.ellipse([x0, y0, x1, y1], fill="white", outline="black", width=2)

    # Draw text centered
    text_x = center_x - text_w // 2
    text_y = center_y - text_h // 2
    draw.text((text_x, text_y), text, fill="black", font=font)


def compose_manga_page(
    panel_images: list[Path],
    script: MangaScript,
    output_path: Path,
    title: str = "",
) -> Path:
    """
    Compose 4 panel images into a complete manga page.

    Layout (2x2 grid):
    +----------+----------+
    | Panel 1  | Panel 2  |
    +----------+----------+
    | Panel 3  | Panel 4  |
    +----------+----------+

    Args:
        panel_images: List of 4 panel image paths
        script: The manga script (for dialogue and metadata)
        output_path: Where to save the composed page
        title: Optional title to display at top

    Returns:
        Path to saved manga page
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Title bar height
    title_height = 50 if (title or script.title) else 0
    total_height = PAGE_HEIGHT + title_height

    # Create canvas (white background)
    page = Image.new("RGB", (PAGE_WIDTH, total_height), color="white")
    draw = ImageDraw.Draw(page)

    # Load fonts
    font = _load_font(FONT_SIZE)
    title_font = _load_font(TITLE_FONT_SIZE, bold=True)

    # Draw title
    display_title = title or script.title
    if display_title:
        draw.rectangle([0, 0, PAGE_WIDTH, title_height], fill="black")
        bbox = draw.textbbox((0, 0), display_title, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((PAGE_WIDTH - tw) // 2, (title_height - (bbox[3] - bbox[1])) // 2),
            display_title,
            fill="white",
            font=title_font,
        )

    # Panel layout: 2x2 grid
    panel_w = (PAGE_WIDTH - MARGIN * 2 - PANEL_GAP) // 2
    panel_h = (PAGE_HEIGHT - MARGIN * 2 - PANEL_GAP) // 2

    positions = [
        (MARGIN, MARGIN + title_height),                          # Panel 1: top-left
        (MARGIN + panel_w + PANEL_GAP, MARGIN + title_height),   # Panel 2: top-right
        (MARGIN, MARGIN + panel_h + PANEL_GAP + title_height),   # Panel 3: bottom-left
        (MARGIN + panel_w + PANEL_GAP, MARGIN + panel_h + PANEL_GAP + title_height),  # Panel 4: bottom-right
    ]

    for i, (panel_path, panel_script) in enumerate(zip(panel_images, script.panels)):
        x, y = positions[i]

        # Draw panel border
        draw.rectangle(
            [x - PANEL_BORDER, y - PANEL_BORDER, x + panel_w + PANEL_BORDER, y + panel_h + PANEL_BORDER],
            outline="black",
            width=PANEL_BORDER,
        )

        # Load and paste panel image
        if panel_path.exists():
            try:
                panel_img = Image.open(panel_path).convert("RGB")
                panel_img = panel_img.resize((panel_w, panel_h), Image.LANCZOS)
                page.paste(panel_img, (x, y))
            except Exception as e:
                logger.error(f"Failed to load panel image {panel_path}: {e}")
                # Draw placeholder
                draw.rectangle([x, y, x + panel_w, y + panel_h], fill="#f0f0f0")
                draw.text((x + 10, y + panel_h // 2), f"Panel {i+1}", fill="gray", font=font)
        else:
            # Placeholder for missing panel
            draw.rectangle([x, y, x + panel_w, y + panel_h], fill="#f0f0f0")
            draw.text((x + 10, y + panel_h // 2), f"Panel {i+1}\n(missing)", fill="gray", font=font)

        # Draw dialogue bubble at top of panel
        if panel_script.dialogue:
            bubble_x = x + panel_w // 2
            bubble_y = y + 30  # near the top
            _draw_dialogue_bubble(
                draw=draw,
                text=panel_script.dialogue,
                center_x=bubble_x,
                center_y=bubble_y,
                font=font,
                max_width=panel_w - 20,
            )

        # Panel number indicator
        draw.text((x + 4, y + 4), str(i + 1), fill="black", font=font)

    page.save(output_path, "PNG")
    logger.info(f"Manga page saved to {output_path}")
    return output_path
