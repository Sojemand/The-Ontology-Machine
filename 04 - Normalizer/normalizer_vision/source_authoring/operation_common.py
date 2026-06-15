"""Shared helpers for source-authoring operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..semantic_release import publish_semantic_release as _default_publish_semantic_release
from ..taxonomy_compile import ensure_compiled_taxonomy_assets as _default_ensure_compiled_taxonomy_assets
from ..taxonomy_sources import policy as source_policy


def required_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()


def optional_text(value: Any, *, label: str) -> str | None:
    if value in (None, ""):
        return None
    return required_text(value, label=label)


def required_positive_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} muss eine positive Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} muss eine positive Ganzzahl sein.") from None
    if parsed < 1:
        raise ValueError(f"{label} muss eine positive Ganzzahl sein.")
    return parsed


def optional_locale(value: Any, *, label: str) -> str | None:
    if value in (None, ""):
        return None
    return source_policy.require_locale(value, label=label)


def locale_source(target_locale: str | None) -> str:
    return "explicit_target_locale" if target_locale is not None else "release.default_runtime_locale"


def ensure_compiled(project_root, *, target_locale: str | None):
    compiler = _facade_attr("ensure_compiled_taxonomy_assets", _default_ensure_compiled_taxonomy_assets)
    if target_locale is None:
        return compiler(project_root)
    return compiler(project_root, target_locale=target_locale)


def publish_release(project_root, output_path: Path | None, *, target_locale: str | None):
    publisher = _facade_attr("publish_semantic_release", _default_publish_semantic_release)
    if target_locale is None:
        return publisher(project_root, output_path)
    return publisher(project_root, output_path, target_locale=target_locale)


def _facade_attr(name: str, default):
    from . import operations as operations_facade

    return getattr(operations_facade, name, default)


def optional_bundle_path(value: Any, *, label: str) -> Path | None:
    if value in (None, ""):
        return None
    return required_bundle_path(value, label=label)


def required_bundle_path(value: Any, *, label: str) -> Path:
    path = Path(required_text(value, label=label)).expanduser()
    if path.exists() and path.is_dir():
        raise ValueError(f"{label} muss auf eine .json-Datei zeigen, nicht auf ein Verzeichnis.")
    if path.suffix.casefold() != ".json":
        raise ValueError(f"{label} muss auf eine .json-Datei zeigen.")
    return path
