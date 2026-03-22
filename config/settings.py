from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-3-flash-preview"
    gemini_image_model: str = "gemini-3.1-flash-image-preview"

    data_dir: Path = Path("data")
    characters_dir: Path = Path("data/characters")
    manga_dir: Path = Path("data/manga")
    index_file: Path = Path("data/index.json")
    assets_dir: Path = Path("assets")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
