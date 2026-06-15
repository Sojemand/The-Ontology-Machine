"""Corpus-root resolution for artifact-owned DB provisioning."""

from __future__ import annotations

from pathlib import Path

from ..context import ModuleContext


def resolve_orchestrator_corpus_root(
    context: ModuleContext,
    explicit_corpus_root: str | Path | None = None,
) -> Path:
    explicit_root = _resolve_explicit_corpus_root(context, explicit_corpus_root)
    if explicit_root is not None:
        return explicit_root
    raise ValueError(
        "Confirmation-Artefakt muss corpus_root explizit setzen; "
        "Corpus Builder liest keinen Orchestrator-UI-State als Fallback."
    )


def _resolve_explicit_corpus_root(context: ModuleContext, value: str | Path | None) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = context.resolve_path(path)
    return path.resolve()


__all__ = ["resolve_orchestrator_corpus_root"]
