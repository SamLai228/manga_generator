"""
Manga generation API endpoints.
"""
import json
import logging
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import FileResponse

from models.manga import GenerateMangaRequest, MangaJob, MangaScript
from services.manga_generator.story_parser import parse_story
from services.manga_generator.panel_enricher import build_page_prompt
from services.manga_generator.character_retriever import retrieve_characters_for_script_with_overrides
from services.gemini.client import generate_image
from config.settings import settings

router = APIRouter(prefix="/api/manga", tags=["manga"])
logger = logging.getLogger(__name__)


def _load_job(job_id: str) -> MangaJob:
    job_dir = settings.manga_dir / job_id
    meta_path = job_dir / "metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    with open(meta_path, "r") as f:
        return MangaJob(**json.load(f))


def _save_job(job: MangaJob) -> None:
    job_dir = settings.manga_dir / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    meta_path = job_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(job.model_dump(), f, ensure_ascii=False, indent=2, default=str)


async def _save_style_refs(uploads: list[UploadFile], job_dir: Path) -> list[Path]:
    paths = []
    for i, upload in enumerate(uploads):
        suffix = Path(upload.filename).suffix if upload.filename else ".png"
        path = job_dir / f"style_ref_{i}{suffix}"
        with open(path, "wb") as f:
            f.write(await upload.read())
        paths.append(path)
    return paths


def _run_manga_generation(job_id: str, story_text: str, style_hint: str, selected_character_ids: list[str] = [], style_ref_paths: list[Path] = []) -> None:
    """Background task for full manga generation pipeline."""
    job = _load_job(job_id)
    job.status = "processing"
    _save_job(job)

    try:
        job_dir = settings.manga_dir / job_id

        # Step 1: Parse story
        logger.info(f"[{job_id}] Parsing story...")
        script = parse_story(story_text)
        job.script = script
        _save_job(job)

        # Step 2: Generate single 4-panel manga image
        logger.info(f"[{job_id}] Generating manga page...")
        all_names = [name for panel in script.panels for name in panel.characters]
        character_entries = retrieve_characters_for_script_with_overrides(all_names, selected_character_ids)
        prompt, reference_images = build_page_prompt(script, character_entries, style_hint, style_ref_paths)
        output_path = job_dir / "page.png"
        generate_image(prompt=prompt, output_path=output_path, reference_images=reference_images or None)
        job.output_path = str(output_path)
        job.status = "done"
        _save_job(job)

        logger.info(f"[{job_id}] Manga generation complete!")

    except Exception as e:
        logger.error(f"[{job_id}] Generation failed: {e}", exc_info=True)
        job.status = "error"
        job.error = str(e)
        _save_job(job)


@router.post("/parse")
def parse_story_only(request: GenerateMangaRequest):
    """
    Parse story into 4-panel script without generating images.
    Useful for previewing the script before full generation.
    """
    try:
        script = parse_story(request.story_text)
        return script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_manga(
    background_tasks: BackgroundTasks,
    story_text: str = Form(...),
    style_hint: str = Form(default="manga, black and white, clean lineart"),
    selected_character_ids: str = Form(default="[]"),
    style_ref_files: list[UploadFile] = File(default=[]),
):
    """
    Start async manga generation job.
    Returns job_id to poll for status.
    """
    job_id = str(uuid.uuid4())[:8]
    job = MangaJob(
        id=job_id,
        story_text=story_text,
        status="pending",
        created_at=datetime.utcnow(),
    )
    _save_job(job)

    job_dir = settings.manga_dir / job_id
    style_ref_paths = await _save_style_refs(style_ref_files[:3], job_dir)

    char_ids = json.loads(selected_character_ids)

    background_tasks.add_task(
        _run_manga_generation,
        job_id=job_id,
        story_text=story_text,
        style_hint=style_hint,
        selected_character_ids=char_ids,
        style_ref_paths=style_ref_paths,
    )

    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Get manga generation job status and metadata."""
    return _load_job(job_id)


@router.get("/jobs/{job_id}/page")
def get_manga_page(job_id: str):
    """Download the generated manga page image."""
    job = _load_job(job_id)
    if job.status != "done":
        raise HTTPException(status_code=425, detail=f"Job not done (status: {job.status})")

    page_path = settings.manga_dir / job_id / "page.png"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Page image not found")

    return FileResponse(str(page_path), media_type="image/png")


@router.get("/jobs/{job_id}/panel/{panel_num}")
def get_panel_image(job_id: str, panel_num: int):
    """Get a specific panel image."""
    panel_path = settings.manga_dir / job_id / f"panel_{panel_num}.png"
    if not panel_path.exists():
        raise HTTPException(status_code=404, detail="Panel image not found")
    return FileResponse(str(panel_path), media_type="image/png")


@router.get("/jobs")
def list_jobs():
    """List all manga generation jobs."""
    manga_dir = settings.manga_dir
    if not manga_dir.exists():
        return []

    jobs = []
    for job_dir in sorted(manga_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        meta_path = job_dir / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    jobs.append(json.load(f))
            except Exception:
                pass
    return jobs
