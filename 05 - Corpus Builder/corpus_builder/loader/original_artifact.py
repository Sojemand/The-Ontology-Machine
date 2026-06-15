"""Bounded optional loading for cold original-artifact payloads."""

from __future__ import annotations

import mimetypes
from pathlib import Path


def load_original_artifact(
    file_path: str,
    *,
    enabled: bool,
    max_bytes: int | None,
) -> tuple[str | None, str | None, bytes | None]:
    path = Path(str(file_path or "").strip()).expanduser()
    if not str(path):
        return None, None, None
    file_name = path.name or None
    media_type = mimetypes.guess_type(str(path))[0]
    if not enabled:
        return file_name, media_type, None
    try:
        if not path.exists() or not path.is_file():
            return file_name, media_type, None
        if max_bytes is not None and max_bytes > 0 and path.stat().st_size > max_bytes:
            return file_name, media_type, None
        blob = path.read_bytes()
    except OSError:
        return file_name, media_type, None
    if max_bytes is not None and max_bytes > 0 and len(blob) > max_bytes:
        return file_name, media_type, None
    return file_name, media_type, blob


__all__ = ["load_original_artifact"]
