"""
Parse story text into structured 4-panel manga script using Gemini.
"""
import json
import logging
import re

from services.gemini.client import generate_text
from models.manga import MangaScript, PanelScript

logger = logging.getLogger(__name__)

STORY_PARSER_PROMPT = """You are a manga storyboard artist. Parse the following story into exactly 4 manga panels.

Story: {story_text}

Return a JSON object with this exact structure:
{{
  "title": "short title for the manga",
  "story_summary": "one sentence summary",
  "panels": [
    {{
      "panel_number": 1,
      "scene": "brief scene description (setting/environment)",
      "characters": ["character name 1", "character name 2"],
      "action": "what characters are doing",
      "camera": "close-up|medium shot|wide shot|bird's eye|worm's eye",
      "dialogue": "any speech (empty string if none)",
      "mood": "the emotional tone of this panel"
    }},
    ... (exactly 4 panels total)
  ]
}}

Guidelines:
- Distribute the story naturally across 4 panels
- Panel 1: Setup/introduction
- Panel 2: Rising action or development
- Panel 3: Climax or turning point
- Panel 4: Resolution or punchline
- Keep dialogue short (under 20 characters per panel)
- Character names should match exactly as they appear in the story

Return ONLY the JSON, no other text."""


def parse_story(story_text: str) -> MangaScript:
    """
    Parse a story text into a structured 4-panel MangaScript.

    Args:
        story_text: The story/plot text in any language

    Returns:
        MangaScript with 4 PanelScript objects
    """
    prompt = STORY_PARSER_PROMPT.format(story_text=story_text)

    try:
        raw = generate_text(prompt)
        return _parse_script_response(raw, story_text)
    except Exception as e:
        logger.error(f"Story parsing failed: {e}")
        return _create_fallback_script(story_text)


def _parse_script_response(raw: str, story_text: str) -> MangaScript:
    """Parse raw Gemini response into MangaScript."""
    raw = raw.strip()

    # Remove markdown code blocks
    if "```json" in raw:
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
    elif "```" in raw:
        raw = re.sub(r"```\s*", "", raw)

    raw = raw.strip()

    try:
        data = json.loads(raw)
        panels = []
        for p in data.get("panels", []):
            panels.append(PanelScript(
                panel_number=p.get("panel_number", len(panels) + 1),
                scene=p.get("scene", ""),
                characters=p.get("characters", []),
                action=p.get("action", ""),
                camera=p.get("camera", "medium shot"),
                dialogue=p.get("dialogue", ""),
                mood=p.get("mood", ""),
            ))

        # Ensure exactly 4 panels
        while len(panels) < 4:
            panels.append(PanelScript(
                panel_number=len(panels) + 1,
                scene="continuation",
                characters=[],
                action="scene continues",
                camera="medium shot",
                dialogue="",
                mood="neutral",
            ))
        panels = panels[:4]

        return MangaScript(
            title=data.get("title", "Untitled"),
            story_summary=data.get("story_summary", story_text[:100]),
            panels=panels,
        )
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse story script JSON: {e}")
        return _create_fallback_script(story_text)


def _create_fallback_script(story_text: str) -> MangaScript:
    """Create a basic 4-panel script as fallback."""
    words = story_text.split("，") if "，" in story_text else story_text.split(",")
    panels = []
    for i in range(4):
        scene_text = words[i].strip() if i < len(words) else f"Scene {i+1}"
        panels.append(PanelScript(
            panel_number=i + 1,
            scene=scene_text,
            characters=[],
            action=scene_text,
            camera="medium shot",
            dialogue="",
            mood="neutral",
        ))
    return MangaScript(
        title="Untitled",
        story_summary=story_text[:100],
        panels=panels,
    )
