"""Semantic corpus-db merge flows for service and contract surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..semantic_release.merge_workflow import (
    build_merge_preflight,
    merge_corpus_databases as merge_corpus_databases_impl,
)


def merge_preflight(
    context: ModuleContext,
    *,
    source_db_path: str | Path,
    target_db_path: str | Path,
) -> dict[str, Any]:
    return build_merge_preflight(
        source_db_path=context.resolve_path(source_db_path),
        target_db_path=context.resolve_path(target_db_path),
    )


def merge_corpus_databases(
    context: ModuleContext,
    *,
    source_db_path: str | Path,
    target_db_path: str | Path,
    snapshot_risk_confirmation_artifact_path: str | Path | None = None,
    collision_resolution_artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    return merge_corpus_databases_impl(
        source_db_path=context.resolve_path(source_db_path),
        target_db_path=context.resolve_path(target_db_path),
        snapshot_risk_confirmation_artifact_path=(
            context.resolve_path(snapshot_risk_confirmation_artifact_path)
            if snapshot_risk_confirmation_artifact_path is not None
            else None
        ),
        collision_resolution_artifact_path=(
            context.resolve_path(collision_resolution_artifact_path)
            if collision_resolution_artifact_path is not None
            else None
        ),
    )


__all__ = ["merge_corpus_databases", "merge_preflight"]
