"""Workflow stage for standalone artifact scans and corpus rebuilds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..models.types import LoadBundle
from ..services.bundle_adapter import build_load_bundle
from ..services.config import load_module_config, resolve_corpus_db_path
from ..services.corpus_workflow import load_batch
from .adapter import (
    projection_preview_rows,
    register_projection_preview,
    resolve_artifact_clusters,
    resolve_cluster_sidecars,
)
from .rebuild_release import (
    replace_existing_db_files,
    resolve_rebuild_release,
    seed_rebuild_release_snapshot,
    validate_rebuild_payloads,
)


def build_rebuild_bundles_from_artifacts(
    context: ModuleContext,
    *,
    pipeline_root: str | Path | None = None,
    normalized_dir: str | Path | None = None,
    structured_dir: str | Path | None = None,
    validation_dir: str | Path | None = None,
    raw_dir: str | Path | None = None,
    corpus_db_path: str | Path | None = None,
) -> dict[str, Any]:
    config = (
        None
        if corpus_db_path is not None and str(corpus_db_path).strip()
        else load_module_config(context)
    )
    resolved_root, clusters = resolve_artifact_clusters(
        context,
        pipeline_root=pipeline_root,
        normalized_dir=normalized_dir,
        structured_dir=structured_dir,
        validation_dir=validation_dir,
        raw_dir=raw_dir,
    )

    bundles: list[LoadBundle] = []
    preview_rows: dict[str, Any] = {}
    invalid_projection_files: list[str] = []
    missing_structured = 0
    missing_validation = 0
    missing_raw = 0
    for cluster in clusters:
        for normalized_path in cluster.normalized_files:
            relative_path, structured_path, validation_path, raw_path = resolve_cluster_sidecars(cluster, normalized_path)
            if cluster.structured_dir is not None and structured_path is None:
                missing_structured += 1
            if cluster.validation_dir is not None and validation_path is None:
                missing_validation += 1
            if cluster.raw_dir is not None and raw_path is None:
                missing_raw += 1
            evidence_structured = structured_path if structured_path is not None and validation_path is not None else None
            evidence_validation = validation_path if structured_path is not None and validation_path is not None else None
            register_projection_preview(
                preview_rows,
                invalid_projection_files,
                normalized_path=normalized_path,
                cluster_root=cluster.root,
                relative_path=relative_path,
            )
            bundles.append(
                build_load_bundle(
                    context,
                    normalized_path=normalized_path,
                    structured_path=evidence_structured,
                    validation_path=evidence_validation,
                    raw_path=raw_path,
                    corpus_db_path=corpus_db_path,
                    config=config,
                )
            )

    normalized_dirs = [str(cluster.normalized_dir) for cluster in clusters]
    structured_dirs = [str(cluster.structured_dir) for cluster in clusters if cluster.structured_dir is not None]
    validation_dirs = [str(cluster.validation_dir) for cluster in clusters if cluster.validation_dir is not None]
    raw_dirs = [str(cluster.raw_dir) for cluster in clusters if cluster.raw_dir is not None]
    artifact_roots = [str(cluster.root) for cluster in clusters]
    return {
        "pipeline_root": str(resolved_root) if resolved_root is not None else "",
        "artifact_roots": artifact_roots,
        "cluster_count": len(clusters),
        "normalized_dirs": normalized_dirs,
        "structured_dirs": structured_dirs,
        "validation_dirs": validation_dirs,
        "raw_dirs": raw_dirs,
        "normalized_dir": normalized_dirs[0] if normalized_dirs else "",
        "structured_dir": structured_dirs[0] if structured_dirs else "",
        "validation_dir": validation_dirs[0] if validation_dirs else "",
        "raw_dir": raw_dirs[0] if raw_dirs else "",
        "bundle_count": len(bundles),
        "missing_structured_count": missing_structured,
        "missing_validation_count": missing_validation,
        "missing_raw_count": missing_raw,
        "projection_preview": projection_preview_rows(preview_rows),
        "invalid_projection_files": invalid_projection_files,
        "bundles": bundles,
    }


def rebuild_corpus_from_artifacts(
    context: ModuleContext,
    *,
    pipeline_root: str | Path | None = None,
    normalized_dir: str | Path | None = None,
    structured_dir: str | Path | None = None,
    validation_dir: str | Path | None = None,
    raw_dir: str | Path | None = None,
    corpus_db_path: str | Path | None = None,
    release_path: str | Path | None = None,
    replace_existing: bool = True,
) -> dict[str, Any]:
    bundle_info = build_rebuild_bundles_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        normalized_dir=normalized_dir,
        structured_dir=structured_dir,
        validation_dir=validation_dir,
        raw_dir=raw_dir,
        corpus_db_path=corpus_db_path,
    )
    bundles = list(bundle_info["bundles"])
    config = load_module_config(context)
    release, active_release_path = resolve_rebuild_release(
        context,
        config=config,
        corpus_db_path=corpus_db_path,
        release_path=release_path,
        replace_existing=replace_existing,
    )
    validate_rebuild_payloads(bundles, release)

    db_path = Path(resolve_corpus_db_path(context, corpus_db_path, config=config))
    replaced_existing = replace_existing_db_files(db_path) if replace_existing else False
    seeded_release_snapshot = seed_rebuild_release_snapshot(
        db_path,
        release,
        release_path=active_release_path,
    )
    result = load_batch(context, bundles)
    return {
        **bundle_info,
        "active_release_id": release.get("release_id"),
        "active_release_version": release.get("release_version"),
        "active_release_fingerprint": release.get("fingerprint"),
        "active_release_path": str(active_release_path),
        "corpus_db_path": str(db_path),
        "release_fingerprint": release.get("release_fingerprint") or release.get("fingerprint"),
        "replace_existing": bool(replace_existing),
        "replaced_existing": replaced_existing,
        "seeded_release_snapshot": seeded_release_snapshot,
        "result": result,
    }
