"""OCR execution boundary for embedded DOCX images."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .types import WordStageError


def run_embedded_image_ocr(
    image_path: Path,
    config: dict[str, Any],
    *,
    extract_page_assets: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    timeout = int(config.get("embedded_image_ocr_timeout_seconds", 120) or 120)
    payload = extract_page_assets([str(image_path)], source_path=image_path, timeout_seconds=timeout)
    if not isinstance(payload, dict):
        raise WordStageError("adapter.ocr", f"Embedded-Image-OCR lieferte kein Objekt fuer {image_path.name}")
    if str(payload.get("status") or "").strip().lower() != "success":
        errors = [str(item).strip() for item in payload.get("errors", []) if str(item).strip()]
        raise WordStageError(
            "adapter.ocr",
            f"Embedded-Image-OCR fehlgeschlagen fuer {image_path.name}: {(errors[0] if errors else 'unbekannter Fehler')[:300]}",
        )
    return payload


def config_enabled(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
