from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PanelScript(BaseModel):
    panel_number: int  # 1-4
    scene: str
    characters: list[str]  # character names
    action: str
    camera: str  # e.g. "close-up", "wide shot", "medium shot"
    dialogue: str = ""
    mood: str = ""


class MangaScript(BaseModel):
    title: str = ""
    story_summary: str
    panels: list[PanelScript]  # exactly 4


class MangaJob(BaseModel):
    id: str
    story_text: str
    script: Optional[MangaScript] = None
    panel_images: list[str] = []  # filenames
    output_path: str = ""
    status: str = "pending"  # pending, processing, done, error
    error: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GenerateMangaRequest(BaseModel):
    story_text: str
    style_hint: str = "manga, black and white, clean lineart"
