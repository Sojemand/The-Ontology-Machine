"""Page-image asset loading for Optimizer OCR calls."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from .errors import LlmOcrConfigurationError


_SUPPORTED_IMAGE_SUFFIXES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def load_image_assets(image_paths: list[str]) -> list[dict[str, str]]:
    if not image_paths:
        raise LlmOcrConfigurationError("LLM-OCR benoetigt mindestens ein gerendertes Page-Asset.")
    assets: list[dict[str, str]] = []
    for index, raw_path in enumerate(image_paths, start=1):
        path = Path(str(raw_path))
        if not path.is_file():
            raise LlmOcrConfigurationError(f"LLM-OCR Page-Asset fehlt: {path}")
        media_type = media_type_for_path(path)
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        assets.append(
            {
                "page_number": str(index),
                "path": str(path),
                "media_type": media_type,
                "data_url": f"data:{media_type};base64,{encoded}",
            }
        )
    return assets


def media_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _SUPPORTED_IMAGE_SUFFIXES:
        return _SUPPORTED_IMAGE_SUFFIXES[suffix]
    guessed, _encoding = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("image/"):
        return guessed
    raise LlmOcrConfigurationError(f"LLM-OCR unterstuetzt dieses Asset-Format nicht: {path.name}")
