"""Validation helpers for optional module debug_surface metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .exceptions import ModuleRegistryError
from .types import DebugSurfaceSpec


def coerce_debug_surface(
    raw_surface: Any,
    *,
    module_key: str,
    manifest_path: Path,
) -> DebugSurfaceSpec | None:
    if raw_surface is None:
        return None
    if not isinstance(raw_surface, dict):
        raise ModuleRegistryError(f"debug_surface must be an object for {module_key}: {manifest_path}")
    return DebugSurfaceSpec(
        supports_batch=_coerce_bool(raw_surface.get("supports_batch", False)),
        supports_single=_coerce_bool(raw_surface.get("supports_single", False)),
        supports_scan=_coerce_bool(raw_surface.get("supports_scan", False)),
        input_source=_coerce_text(raw_surface.get("input_source"), "input_source", module_key, manifest_path),
        output_source=_coerce_text(raw_surface.get("output_source"), "output_source", module_key, manifest_path),
        controls=_coerce_items(raw_surface.get("controls"), "controls", module_key, manifest_path),
        artifacts=_coerce_items(raw_surface.get("artifacts"), "artifacts", module_key, manifest_path),
    )


def _coerce_bool(value: Any) -> bool:
    return bool(value)


def _coerce_text(value: Any, field_name: str, module_key: str, manifest_path: Path) -> str:
    text = str(value or "").strip()
    if not text:
        raise ModuleRegistryError(f"debug_surface.{field_name} is missing for {module_key}: {manifest_path}")
    return text


def _coerce_items(value: Any, field_name: str, module_key: str, manifest_path: Path) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ModuleRegistryError(f"debug_surface.{field_name} must be an array for {module_key}: {manifest_path}")
    items = tuple(str(item).strip() for item in value if str(item).strip())
    if len(items) != len(set(items)):
        raise ModuleRegistryError(
            f"debug_surface.{field_name} contains duplicates for {module_key}: {manifest_path}"
        )
    return items
