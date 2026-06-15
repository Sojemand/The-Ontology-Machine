"""Ontology-layer service workflows owned by Corpus Builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database.repository_connection import connect
from ..database.workflow import ensure_schema
from ..ontology import basic_relation_mining
from .config import resolve_corpus_db_path


def run_basic_relation_mining(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run deterministic source-document/base-graph mining on an existing corpus DB."""

    resolved = Path(resolve_corpus_db_path(context, corpus_db_path)).resolve()
    if not resolved.exists():
        raise ValueError(f"Corpus DB existiert nicht: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Corpus DB muss eine Datei sein: {resolved}")

    conn = connect(str(resolved))
    try:
        ensure_schema(conn)
        report = basic_relation_mining(conn, dry_run=dry_run)
    finally:
        conn.close()
    return {
        "status": report.get("status") or "unknown",
        "corpus_db_path": str(resolved),
        "dry_run": dry_run,
        "report": report,
    }


__all__ = ["run_basic_relation_mining"]
