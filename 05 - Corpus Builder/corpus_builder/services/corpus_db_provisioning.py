"""Provisioning helpers for new artifact-owned corpus databases."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

from ..context import ModuleContext
from ..models.serialization import atomic_json_write
from .config import load_module_config, resolve_corpus_db_path
from .corpus_db_confirmation import load_new_corpus_db_confirmation
from .corpus_root_resolution import resolve_orchestrator_corpus_root

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_DATABASE_LABEL_FILENAME_LIMIT = 72
_TAXONOMY_LOCALE_FILENAME_LIMIT = 24


def create_and_activate_new_corpus_db(
    context: ModuleContext,
    *,
    release_path: str | Path,
    confirmation_artifact_path: str | Path,
    activate_release_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    confirmation = load_new_corpus_db_confirmation(
        confirmation_artifact_path,
        expected_action="create_and_activate_new_corpus_db",
    )
    provisioned = provision_new_corpus_db_path(
        context,
        database_label=str(confirmation["database_label"]),
        taxonomy_locale=str(confirmation["taxonomy_locale"]),
        corpus_root=confirmation.get("corpus_root"),
    )
    detail = activate_release_fn(
        context,
        release_path=release_path,
        corpus_db_path=str(provisioned["corpus_db_path"]),
    )
    persist_default_corpus_db_path(context, provisioned["corpus_db_path"])
    return {
        **detail,
        **_provisioning_result(provisioned),
    }


def create_and_rebuild_new_corpus_db(
    context: ModuleContext,
    *,
    confirmation_artifact_path: str | Path,
    rebuild_fn: Callable[..., dict[str, Any]],
    pipeline_root: str | Path | None = None,
    normalized_dir: str | Path | None = None,
    structured_dir: str | Path | None = None,
    validation_dir: str | Path | None = None,
    raw_dir: str | Path | None = None,
    release_path: str | Path | None = None,
) -> dict[str, Any]:
    confirmation = load_new_corpus_db_confirmation(
        confirmation_artifact_path,
        expected_action="create_and_rebuild_new_corpus_db",
    )
    provisioned = provision_new_corpus_db_path(
        context,
        database_label=str(confirmation["database_label"]),
        taxonomy_locale=str(confirmation["taxonomy_locale"]),
        corpus_root=confirmation.get("corpus_root"),
    )
    detail = rebuild_fn(
        context,
        pipeline_root=pipeline_root,
        normalized_dir=normalized_dir,
        structured_dir=structured_dir,
        validation_dir=validation_dir,
        raw_dir=raw_dir,
        release_path=release_path,
        corpus_db_path=str(provisioned["corpus_db_path"]),
        replace_existing=False,
    )
    persist_default_corpus_db_path(context, provisioned["corpus_db_path"])
    return {
        **detail,
        **_provisioning_result(provisioned),
    }


def provision_new_corpus_db_path(
    context: ModuleContext,
    *,
    database_label: str,
    taxonomy_locale: str,
    corpus_root: str | Path | None = None,
) -> dict[str, object]:
    resolved_corpus_root = resolve_orchestrator_corpus_root(context, explicit_corpus_root=corpus_root)
    safe_label = _safe_segment(database_label, fallback="corpus", max_length=_DATABASE_LABEL_FILENAME_LIMIT)
    safe_locale = _safe_segment(taxonomy_locale.lower(), fallback="und", max_length=_TAXONOMY_LOCALE_FILENAME_LIMIT)
    created_on = date.today().isoformat()
    filename = f"{safe_label}-{created_on}-corpus-{safe_locale}.db"
    db_path = (resolved_corpus_root / filename).resolve()
    _ensure_new_db_target(db_path)
    return {
        "database_label": database_label.strip(),
        "taxonomy_locale": taxonomy_locale.strip().lower(),
        "created_on": created_on,
        "corpus_root": resolved_corpus_root,
        "corpus_db_path": db_path,
        "previous_default_corpus_db_path": resolve_corpus_db_path(
            context,
            None,
            config=load_module_config(context),
        ),
    }


def persist_default_corpus_db_path(context: ModuleContext, corpus_db_path: str | Path) -> None:
    path = Path(corpus_db_path).expanduser().resolve()
    payload = _read_config_payload(context.config_path)
    database = _read_config_database(payload)
    database["corpus_db"] = str(path)
    atomic_json_write(context.config_path, payload)


def resolve_existing_corpus_db_path(context: ModuleContext, corpus_db_path: str | Path | None = None) -> Path:
    config = load_module_config(context)
    resolved = Path(resolve_corpus_db_path(context, corpus_db_path, config=config)).resolve()
    if resolved.exists():
        return resolved
    raise ValueError(
        f"Corpus DB existiert nicht: {resolved}. Fuer eine neue Datenbank nutze den expliziten Neuerstellen-Flow."
    )


def _ensure_new_db_target(db_path: Path) -> None:
    for target in (db_path, db_path.with_name(f"{db_path.name}-shm"), db_path.with_name(f"{db_path.name}-wal")):
        if target.exists():
            raise ValueError(f"Neue Corpus DB existiert bereits: {db_path}")


def _provisioning_result(provisioned: dict[str, object]) -> dict[str, object]:
    return {
        "corpus_db_path": str(provisioned["corpus_db_path"]),
        "corpus_root": str(provisioned["corpus_root"]),
        "database_label": provisioned["database_label"],
        "taxonomy_locale": provisioned["taxonomy_locale"],
        "created_on": provisioned["created_on"],
        "previous_default_corpus_db_path": provisioned["previous_default_corpus_db_path"],
        "default_corpus_db_path": str(provisioned["corpus_db_path"]),
    }


def _read_config_payload(config_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Corpus Config fehlt: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corpus Config ist kein gueltiges JSON: {config_path}") from exc
    except OSError as exc:
        raise ValueError(f"Corpus Config kann nicht gelesen werden: {config_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Corpus Config muss ein JSON-Objekt sein.")
    return payload


def _read_config_database(payload: dict[str, Any]) -> dict[str, Any]:
    database = payload.get("database")
    if not isinstance(database, dict):
        raise ValueError("Corpus Config database muss ein JSON-Objekt sein.")
    corpus_db = database.get("corpus_db")
    if not isinstance(corpus_db, str) or not corpus_db.strip():
        raise ValueError("Corpus Config database.corpus_db muss ein nichtleerer Textpfad sein.")
    return database


def _safe_segment(value: str, *, fallback: str, max_length: int | None = None) -> str:
    cleaned = _SAFE_NAME_RE.sub("-", str(value or "").strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("._-")
    cleaned = cleaned or fallback
    if max_length is None or len(cleaned) <= max_length:
        return cleaned
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:8]
    prefix_length = max_length - len(digest) - 1
    if prefix_length < 1:
        return digest[:max_length]
    prefix = cleaned[:prefix_length].rstrip("._-") or fallback[:prefix_length].rstrip("._-") or fallback
    return f"{prefix[:prefix_length]}-{digest}"


__all__ = [
    "create_and_activate_new_corpus_db",
    "create_and_rebuild_new_corpus_db",
    "load_new_corpus_db_confirmation",
    "persist_default_corpus_db_path",
    "provision_new_corpus_db_path",
    "resolve_existing_corpus_db_path",
    "resolve_orchestrator_corpus_root",
]
