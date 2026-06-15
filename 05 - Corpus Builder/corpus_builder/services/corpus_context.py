"""Owner-local corpus context and empty database flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect
from .config import load_module_config, resolve_corpus_db_path
from .corpus_db_provisioning import persist_default_corpus_db_path


def activate_corpus_context(context: ModuleContext, *, corpus_db_path: str | Path) -> dict[str, Any]:
    """Set the Corpus Builder's owner-local default DB to an existing file."""

    config = load_module_config(context)
    previous_default = resolve_corpus_db_path(context, None, config=config)
    resolved = Path(resolve_corpus_db_path(context, corpus_db_path, config=config)).resolve()
    if not resolved.exists():
        raise ValueError(f"Corpus DB existiert nicht: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Corpus DB muss eine Datei sein: {resolved}")

    from .semantic_status import semantic_status

    status = semantic_status(context, corpus_db_path=resolved)
    persist_default_corpus_db_path(context, resolved)
    return {
        "status": "ok",
        "corpus_db_path": str(resolved),
        "default_corpus_db_path": str(resolved),
        "previous_default_corpus_db_path": previous_default,
        "semantic_status": status,
    }


def create_empty_corpus_db(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path,
    activate_context: bool = False,
) -> dict[str, Any]:
    """Create an empty SQLite corpus DB without activating a semantic release."""

    config = load_module_config(context)
    previous_default = resolve_corpus_db_path(context, None, config=config)
    resolved = Path(resolve_corpus_db_path(context, corpus_db_path, config=config)).resolve()
    _ensure_new_db_target(resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(str(resolved))
    conn.close()
    if activate_context:
        persist_default_corpus_db_path(context, resolved)
    return {
        "status": "ok",
        "corpus_db_path": str(resolved),
        "default_corpus_db_path": str(resolved) if activate_context else previous_default,
        "previous_default_corpus_db_path": previous_default,
        "activated_context": bool(activate_context),
        "active_release_id": None,
        "active_release_version": None,
        "runtime_truth_source": "uninitialized",
    }


def _ensure_new_db_target(db_path: Path) -> None:
    for target in (db_path, db_path.with_name(f"{db_path.name}-shm"), db_path.with_name(f"{db_path.name}-wal")):
        if target.exists():
            raise ValueError(f"Corpus DB existiert bereits: {db_path}")


__all__ = ["activate_corpus_context", "create_empty_corpus_db"]
