"""Where files live on disk. Paths are built from server-generated ids, never from user input.

data/public   is served at /files: overlays, crops, thumbnails, leaf photos with EXIF stripped.
data/private  is never served: original images and engine caches.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.config import get_settings


def public_dir() -> Path:
    return get_settings().data_dir / "public"


def private_dir() -> Path:
    return get_settings().data_dir / "private"


def diagnosis_cache_dir() -> Path:
    return get_settings().data_dir / "cache" / "diagnosis"


def ensure_dirs() -> None:
    for path in (public_dir(), private_dir(), diagnosis_cache_dir()):
        path.mkdir(parents=True, exist_ok=True)


def public_url(relative: str | None) -> str | None:
    return f"/files/{relative}" if relative else None


def field_image_path(field_id: str) -> Path:
    return private_dir() / "fields" / f"{field_id}.jpg"


def scan_private_dir(scan_id: str) -> Path:
    return private_dir() / "scans" / scan_id


def remove_scan_files(scan_id: str) -> None:
    shutil.rmtree(public_dir() / scan_id, ignore_errors=True)
    shutil.rmtree(scan_private_dir(scan_id), ignore_errors=True)


def wipe_all() -> None:
    """Delete every stored file, including cached AI replies and photos (TRD 8.5)."""
    for path in (public_dir(), private_dir(), diagnosis_cache_dir()):
        shutil.rmtree(path, ignore_errors=True)
    ensure_dirs()
