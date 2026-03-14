"""
FastAPI application entry point for the Manga Generator.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from api.routes.characters import router as characters_router
from api.routes.manga import router as manga_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Manga Generator API",
    description="Auto-generate 4-panel manga with character consistency",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(characters_router)
app.include_router(manga_router)

# Serve frontend build
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    # Ensure data directories exist
    settings.characters_dir.mkdir(parents=True, exist_ok=True)
    settings.manga_dir.mkdir(parents=True, exist_ok=True)
    settings.assets_dir.mkdir(parents=True, exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, reload_dirs=["api", "services", "models", "config"])
