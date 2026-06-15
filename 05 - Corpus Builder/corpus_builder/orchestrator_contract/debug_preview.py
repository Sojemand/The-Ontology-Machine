"""Preview builders for Corpus Builder debug actions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..semantic_release import projection_metadata
from ..services import build_load_bundle
from ..standalone_artifacts import build_rebuild_bundles_from_artifacts
from ..standalone_artifacts.policy import validation_suffixes_for_structured


def build_scan_preview(context: ModuleContext, *, input_root: Path, corpus_db_path: Path) -> dict[str, Any]:
    return build_rebuild_bundles_from_artifacts(
        context,
        pipeline_root=input_root,
        corpus_db_path=corpus_db_path,
    )


def build_single_preview(context: ModuleContext, *, source_path: Path, corpus_db_path: Path) -> dict[str, Any]:
    cluster_root, normalized_dir, structured_dir, validation_dir = _cluster_dirs_for_source(source_path)
    relative_path = source_path.relative_to(normalized_dir) if normalized_dir is not None else Path(source_path.name)
    structured_path = _structured_sidecar(relative_path, structured_dir)
    validation_path = _validation_sidecar(relative_path, structured_path, validation_dir)
    preview = {
        "pipeline_root": str(cluster_root or source_path.parent),
        "artifact_roots": [str(cluster_root)] if cluster_root is not None else [],
        "cluster_count": 1,
        "normalized_dirs": [str(normalized_dir)] if normalized_dir is not None else [],
        "structured_dirs": [str(structured_dir)] if structured_dir is not None else [],
        "validation_dirs": [str(validation_dir)] if validation_dir is not None else [],
        "normalized_dir": str(normalized_dir or source_path.parent),
        "structured_dir": str(structured_dir or ""),
        "validation_dir": str(validation_dir or ""),
        "bundle_count": 1,
        "missing_structured_count": int(structured_dir is not None and structured_path is None),
        "missing_validation_count": int(validation_dir is not None and validation_path is None),
        "projection_preview": [_projection_row(source_path, cluster_root, relative_path)],
        "invalid_projection_files": [],
    }
    preview["bundles"] = [
        build_load_bundle(
            context,
            normalized_path=source_path,
            structured_path=structured_path,
            validation_path=validation_path,
            corpus_db_path=corpus_db_path,
        )
    ]
    return preview


def preview_payload(preview: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in preview.items() if key != "bundles"}


def preview_metrics(preview: dict[str, Any]) -> dict[str, int]:
    return {
        "bundle_count": int(preview.get("bundle_count", 0) or 0),
        "projection_count": len(preview.get("projection_preview") or []),
        "missing_structured_count": int(preview.get("missing_structured_count", 0) or 0),
        "missing_validation_count": int(preview.get("missing_validation_count", 0) or 0),
        "loaded": 0,
        "skipped": 0,
        "archived": 0,
        "errors": 0,
    }


def _cluster_dirs_for_source(source_path: Path) -> tuple[Path | None, Path | None, Path | None, Path | None]:
    normalized_dir = _nearest_named_ancestor(source_path, "normalized")
    if normalized_dir is None:
        return None, None, None, None
    cluster_root = normalized_dir.parent
    structured_dir = cluster_root / "structured"
    validation_dir = cluster_root / "validation"
    return (
        cluster_root,
        normalized_dir,
        structured_dir if structured_dir.is_dir() else None,
        validation_dir if validation_dir.is_dir() else None,
    )


def _nearest_named_ancestor(path: Path, name: str) -> Path | None:
    target = name.casefold()
    for parent in path.parents:
        if parent.name.casefold() == target:
            return parent
    return None


def _structured_sidecar(relative_path: Path, structured_dir: Path | None) -> Path | None:
    if structured_dir is None:
        return None
    path = structured_dir / _swap_suffix(relative_path, ".structured.normalized.json", ".structured.json")
    return path if path.exists() and path.is_file() else None


def _validation_sidecar(relative_path: Path, structured_path: Path | None, validation_dir: Path | None) -> Path | None:
    if validation_dir is None:
        return None
    for suffix in validation_suffixes_for_structured(structured_path):
        path = validation_dir / _swap_suffix(relative_path, ".structured.normalized.json", suffix)
        if path.exists() and path.is_file():
            return path
    return None


def _swap_suffix(path: Path, old_suffix: str, new_suffix: str) -> Path:
    if not path.name.endswith(old_suffix):
        raise ValueError(f"Dateiname passt nicht zum erwarteten Suffix {old_suffix}: {path}")
    return path.with_name(path.name[: -len(old_suffix)] + new_suffix)


def _projection_row(source_path: Path, cluster_root: Path | None, relative_path: Path) -> dict[str, object]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    projection_id = str(projection_metadata(payload).get("projection_id") or "").strip() or "<unbekannt>"
    sample_root = cluster_root.name if cluster_root is not None else source_path.parent.name
    sample_path = str(relative_path).replace("\\", "/")
    return {
        "projection_id": projection_id,
        "count": 1,
        "samples": [f"{sample_root}/{sample_path}"],
    }
