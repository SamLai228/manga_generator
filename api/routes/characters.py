"""
Character-related API endpoints.
"""
import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models.character import CharacterTags, CharacterIndexEntry, CharacterMetadata
from services.character_studio.character_registry import register_character, get_character_metadata, update_character_tags
from services.character_studio.character_analyzer import analyze_character_from_images
from services.character_studio.style_extractor import extract_style_from_images
from services.retrieval.tag_store import list_all_characters, search_characters, remove_character, get_index_stats
from config.settings import settings

router = APIRouter(prefix="/api/characters", tags=["characters"])
logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    additional_description: str = ""


class RegisterRequest(BaseModel):
    name: str
    additional_description: str = ""
    confirmed_tags: Optional[CharacterTags] = None
    generate_angles: bool = True


class UpdateTagsRequest(BaseModel):
    tags: CharacterTags


@router.get("/", response_model=list[CharacterIndexEntry])
def list_characters(name: Optional[str] = None):
    """List all characters or search by name."""
    if name:
        return search_characters(name=name)
    return list_all_characters()


@router.get("/stats")
def get_stats():
    """Get character library stats."""
    return get_index_stats()


@router.get("/{character_id}", response_model=CharacterMetadata)
def get_character(character_id: str):
    """Get full character metadata."""
    meta = get_character_metadata(character_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Character not found")
    return meta


@router.get("/{character_id}/image/{filename}")
def get_character_image(character_id: str, filename: str):
    """Serve a character image file."""
    char_dir = settings.characters_dir / character_id
    image_path = char_dir / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")


async def _save_uploads(uploads: list[UploadFile], temp_dir: str, prefix: str) -> list[Path]:
    paths = []
    for upload in uploads:
        suffix = Path(upload.filename).suffix if upload.filename else ".png"
        path = Path(temp_dir) / f"{prefix}_{len(paths)}{suffix}"
        with open(path, "wb") as f:
            f.write(await upload.read())
        paths.append(path)
    return paths


@router.post("/analyze")
async def analyze_character(
    photo_files: list[UploadFile] = File(default=[]),
    style_files: list[UploadFile] = File(default=[]),
    additional_description: str = Form(default=""),
    name: str = Form(default=""),
):
    """
    Analyze reference images and suggest character tags.
    photo_files: real photos for character trait analysis
    style_files: manga style references for art style extraction
    """
    temp_dir = tempfile.mkdtemp()
    try:
        photo_paths = await _save_uploads(photo_files, temp_dir, "photo")
        style_paths = await _save_uploads(style_files, temp_dir, "style")

        try:
            description, tags = await asyncio.to_thread(
                analyze_character_from_images,
                image_paths=photo_paths,
                name=name,
                additional_description=additional_description,
            )
            style = await asyncio.to_thread(
                extract_style_from_images,
                style_paths if style_paths else photo_paths,
            )
        except Exception as e:
            logger.error(f"Character analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        return {
            "description": description,
            "style_description": style,
            "suggested_tags": tags.model_dump(),
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/register")
async def register_new_character(
    photo_files: list[UploadFile] = File(default=[]),
    style_files: list[UploadFile] = File(default=[]),
    name: str = Form(...),
    additional_description: str = Form(default=""),
    generate_angles: bool = Form(default=True),
    tags_json: str = Form(default=""),
):
    """
    Register a new character with optional reference images.
    photo_files: real photos for character analysis
    style_files: manga style references for art style extraction
    """
    temp_dir = tempfile.mkdtemp()
    try:
        photo_paths = await _save_uploads(photo_files, temp_dir, "photo")
        style_paths = await _save_uploads(style_files, temp_dir, "style")

        confirmed_tags = None
        if tags_json:
            import json
            tags_data = json.loads(tags_json)
            confirmed_tags = CharacterTags(**tags_data)

        character = await asyncio.to_thread(
            register_character,
            name=name,
            reference_images=photo_paths,
            style_images=style_paths if style_paths else None,
            additional_description=additional_description,
            confirmed_tags=confirmed_tags,
            generate_angles=generate_angles,
        )
        return character
    except Exception as e:
        logger.error(f"Character registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.patch("/{character_id}/tags")
def update_tags(character_id: str, request: UpdateTagsRequest):
    """Update character tags."""
    updated = update_character_tags(character_id, request.tags)
    if not updated:
        raise HTTPException(status_code=404, detail="Character not found")
    return updated


@router.delete("/{character_id}")
def delete_character(character_id: str):
    """Delete a character from the index (does not delete files)."""
    removed = remove_character(character_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"status": "deleted", "id": character_id}
