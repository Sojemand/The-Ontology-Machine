"""Validation helpers for raw corpus config edit surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SETTINGS_FIELDS = (
    "database.corpus_db",
    "archive.enabled",
    "archive.keep_archived",
    "fts.enabled",
    "fts.tokenizer",
    "source.page_images_dir",
    "source.persist_page_images_in_db",
    "semantic.published_release_path",
    "semantic.active_release_path",
    "semantic.release_report_path",
)
EMBEDDINGS_FIELDS = (
    "embeddings.dimensions",
    "embeddings.batch_size",
    "embeddings.max_text_chars",
)


def validate_settings_surface(data: dict[str, Any], *, module_root: Path) -> dict[str, Any]:
    payload = mapping(data, label="corpus_builder.settings")
    require_exact_keys(payload, SETTINGS_FIELDS, label="corpus_builder.settings")
    return {
        "database.corpus_db": normalized_path(payload.get("database.corpus_db"), module_root, "database.corpus_db"),
        "archive.enabled": required_bool(payload.get("archive.enabled"), field_name="archive.enabled"),
        "archive.keep_archived": required_bool(payload.get("archive.keep_archived"), field_name="archive.keep_archived"),
        "fts.enabled": required_bool(payload.get("fts.enabled"), field_name="fts.enabled"),
        "fts.tokenizer": required_text(payload.get("fts.tokenizer"), field_name="fts.tokenizer"),
        "source.page_images_dir": normalized_path(
            payload.get("source.page_images_dir"),
            module_root,
            "source.page_images_dir",
            allow_empty=True,
        ),
        "source.persist_page_images_in_db": required_bool(
            payload.get("source.persist_page_images_in_db"),
            field_name="source.persist_page_images_in_db",
        ),
        "semantic.published_release_path": normalized_path(
            payload.get("semantic.published_release_path"),
            module_root,
            "semantic.published_release_path",
        ),
        "semantic.active_release_path": normalized_path(
            payload.get("semantic.active_release_path"),
            module_root,
            "semantic.active_release_path",
        ),
        "semantic.release_report_path": normalized_path(
            payload.get("semantic.release_report_path"),
            module_root,
            "semantic.release_report_path",
        ),
    }


def validate_embeddings_surface(data: dict[str, Any]) -> dict[str, Any]:
    payload = mapping(data, label="corpus_builder.embeddings_policy")
    require_exact_keys(payload, EMBEDDINGS_FIELDS, label="corpus_builder.embeddings_policy")
    return {
        "embeddings.dimensions": required_positive_int(payload.get("embeddings.dimensions"), field_name="embeddings.dimensions"),
        "embeddings.batch_size": required_positive_int(payload.get("embeddings.batch_size"), field_name="embeddings.batch_size"),
        "embeddings.max_text_chars": required_positive_int(
            payload.get("embeddings.max_text_chars"),
            field_name="embeddings.max_text_chars",
        ),
    }


def mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return value


def require_exact_keys(payload: dict[str, Any], expected: tuple[str, ...], *, label: str) -> None:
    unknown = sorted(set(payload) - set(expected))
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [field_name for field_name in expected if field_name not in payload]
    if missing:
        raise ValueError(f"{label} enthaelt fehlende Felder: {', '.join(missing)}")


def required_bool(value: object, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} muss true oder false sein.")
    return value


def required_positive_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} muss eine positive Ganzzahl sein.")
    return value


def required_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} muss ein nicht-leerer String sein.")
    return value.strip()


def normalized_path(value: object, module_root: Path, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} muss ein String sein.")
    text = value.strip()
    if not text:
        if allow_empty:
            return ""
        raise ValueError(f"{field_name} muss ein nicht-leerer Pfad sein.")
    resolved = Path(text).expanduser()
    resolved = resolved if resolved.is_absolute() else (module_root / resolved)
    resolved = resolved.resolve()
    try:
        relative = resolved.relative_to(module_root.resolve())
    except ValueError:
        return str(resolved)
    return f"./{relative.as_posix()}"
