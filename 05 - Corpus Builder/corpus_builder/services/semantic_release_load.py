"""Semantic release load and preflight flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect
from ..semantic_release import (
    analyze_release,
    build_activation_preflight,
    load_release_from_path,
    stage_published_release,
    write_release_analysis,
)
from .config import load_module_config, resolve_corpus_db_path


def load_semantic_release(
    context: ModuleContext,
    *,
    release_path: str | Path,
    corpus_db_path: str | Path | None = None,
    write_global_mirrors: bool = True,
) -> dict[str, Any]:
    config = load_module_config(context)
    if write_global_mirrors:
        release, source_path, published_path = stage_published_release(context, config, release_path)
    else:
        source_path = context.resolve_path(release_path)
        release = load_release_from_path(source_path, stage="source_release")
        published_path = source_path
    analysis = analyze_release(release)
    report_path = write_release_analysis(context, config, analysis) if write_global_mirrors else None
    from .semantic_status import semantic_status

    return {
        "release_id": release.get("release_id"),
        "release_version": release.get("release_version"),
        "fingerprint": release.get("fingerprint"),
        "release_fingerprint": release.get("release_fingerprint") or release.get("fingerprint"),
        "source_path": str(source_path),
        "release_path": str(published_path),
        "published_release_path": str(published_path) if write_global_mirrors else None,
        "report_path": str(report_path) if report_path is not None else None,
        "global_mirrors_written": bool(write_global_mirrors),
        "analysis": analysis,
        "status": semantic_status(context, corpus_db_path=corpus_db_path),
    }


def activation_preflight(
    context: ModuleContext,
    *,
    release_path: str | Path,
    corpus_db_path: str | Path | None = None,
) -> dict[str, Any]:
    config = load_module_config(context)
    resolved_db_path = resolve_corpus_db_path(context, corpus_db_path, config=config)
    conn = connect(resolved_db_path) if Path(resolved_db_path).exists() else None
    try:
        return build_activation_preflight(
            context,
            config,
            release_path=release_path,
            corpus_db_path=resolved_db_path,
            conn=conn,
        )
    finally:
        if conn is not None:
            conn.close()
