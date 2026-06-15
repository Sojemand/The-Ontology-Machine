"""Boundary helpers for semantic release file I/O."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.serialization import atomic_json_write
from ..taxonomy_compile import compile_source_package
from ..taxonomy_sources import load_source_package
from .types import SemanticReleasePayload


def load_master_taxonomy_payload(project_root: Path) -> dict[str, Any]:
    compiled = compile_source_package(load_source_package(project_root))
    return compiled.master


def load_local_projection_payloads(project_root: Path, projection_ids: list[str] | None = None) -> list[dict[str, Any]]:
    package = load_source_package(project_root)
    requested = [value.strip() for value in projection_ids or [] if value and value.strip()]
    available = set(package["release"]["projection_ids"])
    if requested:
        missing = [projection_id for projection_id in requested if projection_id not in available]
        if missing:
            raise ValueError(f"Lokale Projection nicht gefunden: {', '.join(missing)}")
    compiled = compile_source_package(
        package,
        projection_ids=requested or None,
    )
    ordered_ids = requested or list(compiled.release["projection_ids"])
    return [
        compiled.projections[projection_id]
        for projection_id in ordered_ids
    ]


def save_semantic_release(path: Path, payload: SemanticReleasePayload | dict[str, Any]) -> None:
    atomic_json_write(path, payload)
