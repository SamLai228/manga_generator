"""
Local JSON index CRUD and tag-based character retrieval.
Manages data/index.json — the master character index.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from models.character import CharacterIndexEntry, CharacterTags
from config.settings import settings

logger = logging.getLogger(__name__)


def _load_index() -> list[dict]:
    """Load the index.json file. Returns empty list if not found."""
    if not settings.index_file.exists():
        return []
    with open(settings.index_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(entries: list[dict]) -> None:
    """Save entries to index.json."""
    settings.index_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.index_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2, default=str)


def add_character(entry: CharacterIndexEntry) -> None:
    """Add or update a character in the index."""
    entries = _load_index()
    # Remove existing entry with same id
    entries = [e for e in entries if e.get("id") != entry.id]
    entries.append(entry.model_dump())
    _save_index(entries)
    logger.info(f"Character '{entry.name}' (id={entry.id}) added to index.")


def remove_character(character_id: str) -> bool:
    """Remove a character from the index. Returns True if found and removed."""
    entries = _load_index()
    new_entries = [e for e in entries if e.get("id") != character_id]
    if len(new_entries) == len(entries):
        return False
    _save_index(new_entries)
    return True


def get_character_by_id(character_id: str) -> Optional[CharacterIndexEntry]:
    """Retrieve a single character by ID."""
    entries = _load_index()
    for e in entries:
        if e.get("id") == character_id:
            return CharacterIndexEntry(**e)
    return None


def get_character_by_name(name: str) -> Optional[CharacterIndexEntry]:
    """Retrieve a character by exact name match (case-insensitive)."""
    entries = _load_index()
    name_lower = name.lower()
    for e in entries:
        if e.get("name", "").lower() == name_lower:
            return CharacterIndexEntry(**e)
    return None


def search_characters(
    name: Optional[str] = None,
    tags: Optional[dict] = None,
    match_all: bool = True,
) -> list[CharacterIndexEntry]:
    """
    Search characters by name and/or tags.

    Args:
        name: Partial name match (case-insensitive)
        tags: Dict of tag_category -> list of values to match
              e.g. {"hair": ["black"], "role": ["protagonist"]}
        match_all: If True, all tag conditions must match (AND).
                   If False, any tag condition matches (OR).

    Returns:
        List of matching CharacterIndexEntry
    """
    entries = _load_index()
    results = []

    for e in entries:
        # Name filter
        if name and name.lower() not in e.get("name", "").lower():
            continue

        # Tag filter
        if tags:
            entry_tags = e.get("tags", {})
            conditions = []
            for category, values in tags.items():
                entry_category_tags = entry_tags.get(category, [])
                # Check if any of the required values exist in this category
                match = any(v.lower() in [t.lower() for t in entry_category_tags] for v in values)
                conditions.append(match)

            if match_all and not all(conditions):
                continue
            if not match_all and not any(conditions):
                continue

        results.append(CharacterIndexEntry(**e))

    return results


def list_all_characters() -> list[CharacterIndexEntry]:
    """Return all characters in the index."""
    entries = _load_index()
    return [CharacterIndexEntry(**e) for e in entries]


def get_index_stats() -> dict:
    """Return summary stats about the index."""
    entries = _load_index()
    return {
        "total_characters": len(entries),
        "character_names": [e.get("name", "") for e in entries],
    }
