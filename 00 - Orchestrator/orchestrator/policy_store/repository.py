"""Repository and cache helpers for orchestrator policy surfaces."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ..bootstrap import ORCHESTRATOR_ROOT
from ..state import atomic_json_write
from .types import (
    ARTIFACT_PUBLICATION_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    ROUTE_INTAKE_SURFACE_ID,
    SURFACE_FILES,
)
from .validation import validate_surface_value

_CACHE: dict[str, tuple[int, int, dict]] = {}


def invalidate_cache(surface_id: str | None = None) -> None:
    if surface_id is None:
        _CACHE.clear()
        return
    _CACHE.pop(surface_id, None)


def load_surface(surface_id: str) -> dict:
    path = surface_path(surface_id)
    stamp = _stamp(path)
    cached = _CACHE.get(surface_id)
    if cached is not None and cached[:2] == stamp:
        return copy.deepcopy(cached[2])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path.name} is invalid: {exc}") from exc
    normalized = validate_surface_value(surface_id, payload)
    _CACHE[surface_id] = (*stamp, normalized)
    return copy.deepcopy(normalized)


def write_surface(surface_id: str, value: dict) -> dict:
    normalized = validate_surface_value(surface_id, value)
    path = surface_path(surface_id)
    atomic_json_write(path, normalized)
    _CACHE[surface_id] = (*_stamp(path), normalized)
    return copy.deepcopy(normalized)


def load_route_intake_policy() -> dict:
    return load_surface(ROUTE_INTAKE_SURFACE_ID)


def load_execution_policy() -> dict:
    return load_surface(EXECUTION_SURFACE_ID)


def load_health_dependency_policy() -> dict:
    return load_surface(HEALTH_DEPENDENCY_SURFACE_ID)


def load_artifact_publication_policy() -> dict:
    return load_surface(ARTIFACT_PUBLICATION_SURFACE_ID)


def surface_path(surface_id: str) -> Path:
    relative = SURFACE_FILES.get(surface_id)
    if not relative:
        raise ValueError(f"Unknown surface: {surface_id}")
    path = ORCHESTRATOR_ROOT / relative
    config_root = ORCHESTRATOR_ROOT / "config"
    if path.parent != config_root or path.suffix.lower() != ".json":
        raise ValueError(f"Policy surface must be located under config/*.json: {relative}")
    return path


def _stamp(path: Path) -> tuple[int, int]:
    if not path.exists():
        raise ValueError(f"Policy file is missing: {path}")
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size
