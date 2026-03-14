from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CharacterTags(BaseModel):
    species: list[str] = []
    hair: list[str] = []
    clothing: list[str] = []
    role: list[str] = []
    personality: list[str] = []
    custom: list[str] = []


class CharacterMetadata(BaseModel):
    id: str
    name: str
    description: str = ""
    style_description: str = ""
    tags: CharacterTags = Field(default_factory=CharacterTags)
    angles: list[str] = []  # available angle image filenames
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reference_images: list[str] = []  # original reference image filenames


class CharacterIndexEntry(BaseModel):
    id: str
    name: str
    tags: CharacterTags
    description: str = ""
    style_description: str = ""
    sheet_path: str = ""  # relative path to sheet.png
