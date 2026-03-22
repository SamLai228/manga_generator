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
from services.manga_generator.character_retriever import retrieve_characters_for_script
from services.gemini.client import generate_image
from services.retrieval.tag_store import get_character_by_id
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

        # Step 2: Resolve characters
        logger.info(f"[{job_id}] Generating manga page...")
        if selected_character_ids:
            # Bypass story name matching — build entries directly from preselected IDs
            character_entries = {}
            for char_id in selected_character_ids:
                entry = get_character_by_id(char_id)
                if entry:
                    character_entries[entry.name] = entry
            # Force every panel to feature the preselected characters
            char_names = list(character_entries.keys())
            for panel in script.panels:
                panel.characters = char_names
        else:
            # No preselection: fall back to name-based lookup from story
            all_names = [name for panel in script.panels for name in panel.characters]
            character_entries = retrieve_characters_for_script(all_names)

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
    char_ids = json.loads(selected_character_ids)
    job = MangaJob(
        id=job_id,
        story_text=story_text,
        style_hint=style_hint,
        selected_character_ids=char_ids,
        status="pending",
        created_at=datetime.utcnow(),
    )
    _save_job(job)

    job_dir = settings.manga_dir / job_id
    style_ref_paths = await _save_style_refs(style_ref_files[:3], job_dir)
    job.style_ref_filenames = [p.name for p in style_ref_paths]
    _save_job(job)

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


@router.post("/jobs/{job_id}/duplicate")
def duplicate_manga_job(job_id: str):
    """Duplicate a manga job, copying all files to a new job directory."""
    job = _load_job(job_id)
    src_dir = settings.manga_dir / job_id

    new_id = str(uuid.uuid4())[:8]
    new_dir = settings.manga_dir / new_id
    shutil.copytree(src_dir, new_dir)

    new_job = job.model_copy(update={"id": new_id, "created_at": datetime.utcnow()})
    if new_job.output_path:
        new_job.output_path = str(new_dir / "page.png")
    meta_path = new_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(new_job.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    return new_job


@router.post("/jobs/{job_id}/edit")
async def edit_manga_page(
    job_id: str,
    instruction: str = Form(...),
    ref_files: list[UploadFile] = File(default=[]),
):
    """Edit an existing manga page with a modification instruction."""
    job = _load_job(job_id)
    if job.status != "done":
        raise HTTPException(status_code=425, detail=f"Job not done (status: {job.status})")

    job_dir = settings.manga_dir / job_id

    # Rebuild character entries from saved IDs
    character_entries = {}
    if job.selected_character_ids:
        for char_id in job.selected_character_ids:
            entry = get_character_by_id(char_id)
            if entry:
                character_entries[entry.name] = entry
        char_names = list(character_entries.keys())
        if job.script:
            for panel in job.script.panels:
                panel.characters = char_names
    elif job.script:
        all_names = [name for panel in job.script.panels for name in panel.characters]
        character_entries = retrieve_characters_for_script(all_names)

    # Rebuild style ref paths from saved filenames
    style_ref_paths = [job_dir / fn for fn in job.style_ref_filenames if (job_dir / fn).exists()]

    # Save uploaded ref files
    uploaded_ref_paths = []
    for i, upload in enumerate(ref_files):
        suffix = Path(upload.filename).suffix if upload.filename else ".png"
        path = job_dir / f"edit_ref_{i}{suffix}"
        with open(path, "wb") as f:
            f.write(await upload.read())
        uploaded_ref_paths.append(path)

    # Build prompt from script
    if job.script:
        base_prompt, reference_images = build_page_prompt(job.script, character_entries, job.style_hint, style_ref_paths)
    else:
        base_prompt = job.story_text
        reference_images = list(style_ref_paths)

    prompt = f"{base_prompt}\n\nUser modification request: {instruction}"

    # Prepend existing page as first reference
    page_path = job_dir / "page.png"
    all_refs = ([page_path] if page_path.exists() else []) + reference_images + uploaded_ref_paths

    output_path = job_dir / "page.png"
    generate_image(prompt=prompt, output_path=output_path, reference_images=all_refs or None)

    return {"status": "ok"}


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
