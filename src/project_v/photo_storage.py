"""Local photo storage for pledged jewellery evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHOTO_ROOT = Path(__file__).parents[2] / "data" / "pledge_photos"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def save_pledge_photos(pledge_number: str, uploaded_files: list[Any]) -> tuple[str, ...]:
    """Save uploaded jewellery photos in a folder named after the pledge number."""
    if not uploaded_files:
        return ()
    pledge_directory = PHOTO_ROOT / pledge_number
    pledge_directory.mkdir(parents=True, exist_ok=True)
    saved_paths: list[str] = []
    for index, uploaded_file in enumerate(uploaded_files, start=1):
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("Only JPG, JPEG, PNG, and WEBP photos are supported.")
        destination = pledge_directory / f"photo_{index}{extension}"
        destination.write_bytes(uploaded_file.getvalue())
        saved_paths.append(str(destination))
    return tuple(saved_paths)
