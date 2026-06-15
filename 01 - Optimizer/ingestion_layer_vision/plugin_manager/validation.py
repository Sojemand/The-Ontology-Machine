"""Hard validation for plugin contracts."""
from __future__ import annotations

from typing import Any

from ..models import ExtractResult, PluginManifest


def build_manifest(data: dict[str, Any], fallback_name: str) -> PluginManifest:
    return PluginManifest(
        name=data.get("name", fallback_name),
        version=data.get("version", "0.0.0"),
        description=data.get("description", ""),
        author=data.get("author", ""),
        formats=data.get("formats", []),
        also_handles=data.get("also_handles", []),
        capabilities=data.get("capabilities", []),
        priority=data.get("priority", 0),
        python_version=data.get("python_version", ">=3.10"),
        system_dependencies=data.get("system_dependencies", []),
        config_schema=data.get("config_schema", {}),
        config=data.get("config", {}),
    )


def parse_result(data: Any) -> ExtractResult:
    if not isinstance(data, dict):
        return ExtractResult(status="error", errors=[f"Ungueltiges Plugin-Payload: {type(data).__name__}"])
    errors: list[str] = []
    raw_errors = data.get("errors", [])
    if isinstance(raw_errors, str):
        if raw_errors.strip():
            errors.append(raw_errors.strip())
    elif isinstance(raw_errors, list):
        for value in raw_errors:
            text = str(value).strip()
            if text:
                errors.append(text)
    elif raw_errors:
        text = str(raw_errors).strip()
        if text:
            errors.append(text)
    status = data.get("status", "error")
    if status != "success" and not errors:
        detail = str(data.get("message") or data.get("error") or "").strip()
        errors = [detail or "Extractor lieferte Fehlerstatus ohne Details"]
    metadata = data.get("metadata", {})
    blocks = data.get("blocks", [])
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(blocks, list):
        blocks = []
    return ExtractResult(
        status=status,
        blocks=blocks,
        metadata=metadata,
        errors=errors,
        processing_time_ms=data.get("processing_time_ms", 0),
        needs_ocr=bool(data.get("needs_ocr", False) or metadata.get("needs_ocr", False)),
    )
