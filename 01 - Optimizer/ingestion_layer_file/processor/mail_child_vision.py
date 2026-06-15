"""Child-vision bridge for rendered mail attachment pages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from optimizer_ocr import extract_page_assets

from ..models import DataBlock

_CHILD_VISION_DEFAULTS: dict[str, Any] = {
    "child_vision_enabled": True,
    "child_vision_timeout_seconds": 120,
}


def extract_child_vision_blocks(processor, image_paths: list[str]) -> list[DataBlock]:
    config = _child_vision_config(processor)
    if not _config_enabled(config.get("child_vision_enabled"), default=True):
        raise RuntimeError("Mail-Anhang verlangt Child-Vision, aber der Child-Vision-Pfad ist deaktiviert.")
    blocks: list[DataBlock] = []
    timeout = int(config.get("child_vision_timeout_seconds", 120) or 120)
    for page_number, image_path in enumerate(image_paths, start=1):
        payload = extract_page_assets([str(Path(image_path))], source_path=image_path, timeout_seconds=timeout)
        if str(payload.get("status") or "").strip().lower() != "success":
            errors = [str(item).strip() for item in payload.get("errors", []) if str(item).strip()]
            raise RuntimeError(errors[0] if errors else f"LLM-OCR fehlgeschlagen fuer {Path(image_path).name}")
        page_blocks = processor._parse_blocks(payload.get("blocks", []))
        for index, block in enumerate(page_blocks):
            block.id = f"ocr_page_{page_number:03d}_{index:04d}"
            block.position.page = page_number
            if block.position.paragraph_index is None:
                block.position.paragraph_index = index
        blocks.extend(page_blocks)
    return blocks


def _child_vision_config(processor) -> dict[str, Any]:
    config = dict(_CHILD_VISION_DEFAULTS)
    manifest = processor._plugin_mgr.get_manifest("docx-python") if hasattr(processor._plugin_mgr, "get_manifest") else None
    manifest_config = getattr(manifest, "config", None)
    if isinstance(manifest_config, dict):
        config.update(manifest_config)
    return config


def _config_enabled(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}
