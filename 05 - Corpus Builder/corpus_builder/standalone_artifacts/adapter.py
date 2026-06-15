"""Artifact adapter stage for standalone rebuild scans and preview metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..context import ModuleContext
from ..semantic_release import projection_metadata
from .policy import validation_suffixes_for_structured


@dataclass(slots=True)
class _ArtifactCluster:
    root: Path
    normalized_dir: Path
    structured_dir: Path | None
    validation_dir: Path | None
    raw_dir: Path | None
    normalized_files: list[Path]


@dataclass(slots=True)
class _ProjectionPreviewRow:
    projection_id: str
    count: int = 0
    samples: list[str] = field(default_factory=list)

    def add_sample(self, cluster_root: Path, relative_path: Path) -> None:
        self.count += 1
        if len(self.samples) < 3:
            sample = str(relative_path).replace("\\", "/")
            self.samples.append(f"{cluster_root.name}/{sample}")

    def as_dict(self) -> dict[str, object]:
        return {"projection_id": self.projection_id, "count": self.count, "samples": list(self.samples)}


def _resolve_optional_dir(context: ModuleContext, value: str | Path | None) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    return context.resolve_path(text) if text else None


def _resolve_explicit_existing_dir(context: ModuleContext, value: str | Path | None, label: str) -> Path | None:
    directory = _resolve_optional_dir(context, value)
    if directory is not None and (not directory.exists() or not directory.is_dir()):
        raise ValueError(f"{label}-Ordner nicht gefunden: {directory}")
    return directory


def _nearest_named_ancestor(path: Path, name: str) -> Path | None:
    target = name.casefold()
    for parent in path.parents:
        if parent.name.casefold() == target:
            return parent
    return None


def _discover_artifact_clusters(pipeline_root: Path) -> list[_ArtifactCluster]:
    cluster_map: dict[Path, _ArtifactCluster] = {}
    for normalized_path in sorted(pipeline_root.rglob("*.structured.normalized.json")):
        normalized_anchor = _nearest_named_ancestor(normalized_path, "normalized")
        if normalized_anchor is None:
            continue
        cluster_root = normalized_anchor.parent
        cluster = cluster_map.setdefault(
            cluster_root,
            _ArtifactCluster(
                root=cluster_root,
                normalized_dir=normalized_anchor,
                structured_dir=(cluster_root / "structured") if (cluster_root / "structured").is_dir() else None,
                validation_dir=(cluster_root / "validation") if (cluster_root / "validation").is_dir() else None,
                raw_dir=(cluster_root / "raw_extracts") if (cluster_root / "raw_extracts").is_dir() else None,
                normalized_files=[],
            ),
        )
        cluster.normalized_files.append(normalized_path)
    return sorted(cluster_map.values(), key=lambda item: str(item.root).casefold())


def _swap_suffix(path: Path, old_suffix: str, new_suffix: str) -> Path:
    if not path.name.endswith(old_suffix):
        raise ValueError(f"Dateiname passt nicht zum erwarteten Suffix {old_suffix}: {path}")
    return path.with_name(path.name[: -len(old_suffix)] + new_suffix)


def resolve_artifact_clusters(
    context: ModuleContext,
    *,
    pipeline_root: str | Path | None = None,
    normalized_dir: str | Path | None = None,
    structured_dir: str | Path | None = None,
    validation_dir: str | Path | None = None,
    raw_dir: str | Path | None = None,
) -> tuple[Path | None, list[_ArtifactCluster]]:
    resolved_root = _resolve_optional_dir(context, pipeline_root)
    explicit_normalized_dir = _resolve_optional_dir(context, normalized_dir)
    if explicit_normalized_dir is not None:
        if not explicit_normalized_dir.exists() or not explicit_normalized_dir.is_dir():
            raise ValueError(f"Normalized-Ordner nicht gefunden: {explicit_normalized_dir}")
        explicit_structured_dir = _resolve_explicit_existing_dir(context, structured_dir, "Structured")
        explicit_validation_dir = _resolve_explicit_existing_dir(context, validation_dir, "Validation")
        explicit_raw_dir = _resolve_explicit_existing_dir(context, raw_dir, "Raw")
        normalized_files = sorted(explicit_normalized_dir.rglob("*.structured.normalized.json"))
        if not normalized_files:
            raise ValueError(f"Keine normalized-Dateien gefunden: {explicit_normalized_dir}")
        return resolved_root, [
            _ArtifactCluster(
                root=resolved_root or explicit_normalized_dir.parent,
                normalized_dir=explicit_normalized_dir,
                structured_dir=explicit_structured_dir,
                validation_dir=explicit_validation_dir,
                raw_dir=explicit_raw_dir,
                normalized_files=normalized_files,
            )
        ]

    if resolved_root is None:
        raise ValueError("Normalized-Ordner fehlt.")
    if not resolved_root.exists() or not resolved_root.is_dir():
        raise ValueError(f"Artefaktordner nicht gefunden: {resolved_root}")
    clusters = _discover_artifact_clusters(resolved_root)
    if not clusters:
        raise ValueError(f"Keine rekursiv gefundenen normalized-Artefakte unter: {resolved_root}")
    return resolved_root, clusters


def resolve_cluster_sidecars(cluster: _ArtifactCluster, normalized_path: Path) -> tuple[Path, Path | None, Path | None, Path | None]:
    relative_path = normalized_path.relative_to(cluster.normalized_dir)
    structured_path = None
    if cluster.structured_dir is not None:
        candidate = cluster.structured_dir / _swap_suffix(relative_path, ".structured.normalized.json", ".structured.json")
        if candidate.exists() and candidate.is_file():
            structured_path = candidate
    validation_path = None
    if cluster.validation_dir is not None:
        for suffix in validation_suffixes_for_structured(structured_path):
            candidate = cluster.validation_dir / _swap_suffix(relative_path, ".structured.normalized.json", suffix)
            if candidate.exists() and candidate.is_file():
                validation_path = candidate
                break
    raw_path = None
    if cluster.raw_dir is not None:
        candidate = cluster.raw_dir / _swap_suffix(relative_path, ".structured.normalized.json", ".raw.json")
        if candidate.exists() and candidate.is_file():
            raw_path = candidate
    return relative_path, structured_path, validation_path, raw_path


def register_projection_preview(
    preview_rows: dict[str, _ProjectionPreviewRow],
    invalid_projection_files: list[str],
    *,
    normalized_path: Path,
    cluster_root: Path,
    relative_path: Path,
) -> None:
    try:
        payload = json.loads(normalized_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("normalized.json ist kein Objekt")
        projection_id = str(projection_metadata(payload).get("projection_id") or "").strip() or "<unbekannt>"
    except Exception as exc:
        projection_id = "<ungueltig>"
        invalid_projection_files.append(f"{normalized_path.name}: {exc}")
    preview_rows.setdefault(projection_id, _ProjectionPreviewRow(projection_id)).add_sample(cluster_root, relative_path)


def projection_preview_rows(preview_rows: dict[str, _ProjectionPreviewRow]) -> list[dict[str, object]]:
    rows = sorted(preview_rows.values(), key=lambda item: (-int(item.count), str(item.projection_id)))
    return [row.as_dict() for row in rows]
