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
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from models.character import CharacterTags, CharacterIndexEntry, CharacterMetadata
from services.character_studio.character_registry import register_character, get_character_metadata, update_character_tags, update_character_name, duplicate_character
from services.character_studio.character_analyzer import analyze_character_from_images
from services.character_studio.style_extractor import extract_style_from_images
from services.retrieval.tag_store import list_all_characters, search_characters, remove_character, get_index_stats
from services.gemini.client import generate_image
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


class UpdateNameRequest(BaseModel):
    name: str


class UpdateTagsRequest(BaseModel):
    tags: CharacterTags


TAG_CATEGORIES = ['species', 'hair', 'clothing', 'role', 'personality', 'custom']


@router.get("/", response_model=list[CharacterIndexEntry])
def list_characters(name: Optional[str] = None, tag: Optional[str] = None):
    """List all characters or search by name and/or tag."""
    if name or tag:
        tags_filter = {cat: [tag] for cat in TAG_CATEGORIES} if tag else None
        return search_characters(name=name, tags=tags_filter, match_all=False)
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
    return FileResponse(
        str(image_path),
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


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


@router.post("/{character_id}/duplicate", response_model=CharacterMetadata)
def duplicate_character_endpoint(character_id: str):
    """Duplicate a character, creating a copy with a new ID."""
    new_character = duplicate_character(character_id)
    if not new_character:
        raise HTTPException(status_code=404, detail="Character not found")
    return new_character


@router.patch("/{character_id}/name")
def update_name(character_id: str, request: UpdateNameRequest):
    """Update character name."""
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    updated = update_character_name(character_id, name)
    if not updated:
        raise HTTPException(status_code=404, detail="Character not found")
    return updated


@router.patch("/{character_id}/tags")
def update_tags(character_id: str, request: UpdateTagsRequest):
    """Update character tags."""
    updated = update_character_tags(character_id, request.tags)
    if not updated:
        raise HTTPException(status_code=404, detail="Character not found")
    return updated


@router.post("/{character_id}/edit-image")
async def edit_character_image(
    character_id: str,
    filename: str = Form(...),
    instruction: str = Form(...),
    ref_files: list[UploadFile] = File(default=[]),
):
    """Edit a character image using Gemini with the existing image (and optional uploads) as reference."""
    img_path = settings.characters_dir / character_id / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    temp_dir = tempfile.mkdtemp()
    try:
        uploaded_paths = await _save_uploads(ref_files, temp_dir, "ref")
        reference_images = [img_path] + uploaded_paths
        prompt = f"Modify this character image: {instruction}. Keep the overall character design and art style consistent."
        await asyncio.to_thread(generate_image, prompt=prompt, output_path=img_path, reference_images=reference_images)
    except Exception as e:
        logger.error(f"Image edit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return {"status": "ok", "filename": filename}


@router.delete("/{character_id}")
def delete_character(character_id: str):
    """Delete a character from the index and remove its files."""
    removed = remove_character(character_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Character not found")
    char_dir = settings.characters_dir / character_id
    if char_dir.exists():
        shutil.rmtree(char_dir, ignore_errors=True)
    return {"status": "deleted", "id": character_id}


@router.get("/{character_id}/reference/{filename}")
def get_reference_image(character_id: str, filename: str):
    """Serve a reference image for a character."""
    char_dir = settings.characters_dir / character_id
    image_path = char_dir / filename
    if not image_path.exists() or image_path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(
        str(image_path),
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
