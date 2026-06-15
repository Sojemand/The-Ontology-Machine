"""Bundle adapter stage for normalized-first service load inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..models.types import CorpusConfig, LoadBundle
from .config import resolve_corpus_db_path


def _require_path_value(value: Any, *, field_name: str) -> str | Path:
    if value is None:
        raise ValueError(f"Feld '{field_name}' fehlt oder ist leer.")
    if isinstance(value, Path):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Feld '{field_name}' muss ein String sein.")
    text = value.strip()
    if not text:
        raise ValueError(f"Feld '{field_name}' fehlt oder ist leer.")
    return text


def build_load_bundle(
    context: ModuleContext,
    *,
    normalized_path: str | Path | None = None,
    structured_path: str | Path | None = None,
    validation_path: str | Path | None = None,
    raw_path: str | Path | None = None,
    corpus_db_path: str | Path | None = None,
    base_dir: Path | None = None,
    config: CorpusConfig | None = None,
) -> LoadBundle:
    normalized_value = _require_path_value(normalized_path, field_name="normalized_path")
    structured_value = _require_path_value(structured_path, field_name="structured_path") if structured_path and str(structured_path).strip() else None
    validation_value = _require_path_value(validation_path, field_name="validation_path") if validation_path and str(validation_path).strip() else None
    raw_value = _require_path_value(raw_path, field_name="raw_path") if raw_path and str(raw_path).strip() else None

    if structured_value is None and validation_value is not None:
        raise ValueError("validation_path darf nur zusammen mit structured_path gesetzt sein.")
    if structured_value is not None and validation_value is None:
        raise ValueError("Feld 'validation_path' fehlt oder ist leer.")

    return LoadBundle(
        normalized_path=context.resolve_path(normalized_value, base_dir=base_dir),
        structured_path=context.resolve_path(structured_value, base_dir=base_dir) if structured_value is not None else None,
        validation_path=context.resolve_path(validation_value, base_dir=base_dir) if validation_value is not None else None,
        raw_path=context.resolve_path(raw_value, base_dir=base_dir) if raw_value is not None else None,
        corpus_db_path=resolve_corpus_db_path(context, corpus_db_path, config=config),
    )
