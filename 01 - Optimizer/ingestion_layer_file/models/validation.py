"""Strict validation helpers for edit-contract model payloads."""
from __future__ import annotations

from typing import Any

from .document_raw import RawExtract

CONFIG_FIELD_ORDER = (
    "max_file_size_mb",
    "max_blocks_per_file",
    "max_cell_text_length",
    "processing_order",
    "plugin_timeout_seconds",
    "parallel_workers",
    "render_dpi",
    "render_width_px",
    "render_height_px",
    "page_margin_pt",
    "default_font_size_pt",
    "code_font_size_pt",
    "heading_font_size_pt",
)
CONFIG_DEFAULTS = {
    "max_file_size_mb": 100,
    "max_blocks_per_file": 50000,
    "max_cell_text_length": 8000,
    "processing_order": "input",
    "plugin_timeout_seconds": 120,
    "parallel_workers": 1,
    "render_dpi": 150,
    "render_width_px": 1240,
    "render_height_px": 1754,
    "page_margin_pt": 54,
    "default_font_size_pt": 10,
    "code_font_size_pt": 9,
    "heading_font_size_pt": 16,
}
CONFIG_MINIMUMS = {
    "max_file_size_mb": 0,
    "max_blocks_per_file": 0,
    "max_cell_text_length": 0,
    "plugin_timeout_seconds": 1,
    "parallel_workers": 1,
    "render_dpi": 72,
    "render_width_px": 100,
    "render_height_px": 100,
    "page_margin_pt": 12,
    "default_font_size_pt": 6,
    "code_font_size_pt": 6,
    "heading_font_size_pt": 8,
}
CONFIG_FIELD_GROUPS = (
    ("Processing", ("max_file_size_mb", "max_blocks_per_file", "max_cell_text_length", "processing_order", "plugin_timeout_seconds", "parallel_workers")),
    ("Rendering/Layout", ("render_dpi", "render_width_px", "render_height_px", "page_margin_pt", "default_font_size_pt", "code_font_size_pt", "heading_font_size_pt")),
)
VALID_PROCESSING_ORDERS = {"input", "format", "size_asc", "size_desc"}


def validate_config_payload(data: Any) -> dict[str, Any]:
    payload = _require_mapping(data, label="config.yaml")
    unknown = sorted(set(payload) - set(CONFIG_FIELD_ORDER))
    if unknown:
        raise ValueError(f"config.yaml enthaelt unbekannte Felder: {', '.join(unknown)}")
    normalized = {}
    for field_name in CONFIG_FIELD_ORDER:
        value = payload.get(field_name, CONFIG_DEFAULTS[field_name])
        if field_name == "processing_order":
            normalized[field_name] = _require_processing_order(value)
            continue
        normalized[field_name] = _require_int(value, field_name=field_name, minimum=CONFIG_MINIMUMS[field_name])
    return normalized


def config_to_dict(config: Any) -> dict[str, Any]:
    if isinstance(config, dict):
        payload = validate_config_payload(config)
    else:
        payload = {field_name: getattr(config, field_name) for field_name in CONFIG_FIELD_ORDER}
    return {field_name: payload[field_name] for field_name in CONFIG_FIELD_ORDER}


def _require_mapping(data: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return data


def _require_int(value: Any, *, field_name: str, minimum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} muss eine Ganzzahl >= {minimum} sein.")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, str):
        value = value.strip()
    try:
        candidate = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} muss eine Ganzzahl >= {minimum} sein.") from exc
    if candidate < minimum:
        raise ValueError(f"{field_name} muss eine Ganzzahl >= {minimum} sein.")
    return candidate


def _require_processing_order(value: Any) -> str:
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in VALID_PROCESSING_ORDERS:
            return candidate
    raise ValueError("processing_order muss einer von input, format, size_asc oder size_desc sein.")


def _validate_raw_extract_consistency(extract: RawExtract) -> None:
    if extract.needs_llm_vision and not extract.image_paths:
        raise ValueError("Vision-Extract erfordert mindestens einen Bildpfad")
