"""Feature-scoped dependency policy for route-aware preflight healthchecks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import policy_store
from . import route_policy

_OPTIMIZER_OCR_DEPENDENCY = "optimizer_ocr"


def build_required_dependencies_by_module(
    records: list[Any],
    *,
    scope: str,
) -> dict[str, tuple[str, ...]]:
    suffix_policy = policy_store.dependency_scope_profile(scope).get("optimizer")
    if not suffix_policy:
        suffix_policy = policy_store.fallback_dependency_profile().get("optimizer")
    if not suffix_policy:
        return {}
    dependencies = optimizer_required_dependencies(records, suffix_policy=suffix_policy)
    if not dependencies:
        return {}
    return {"optimizer": dependencies}


def optimizer_required_dependencies(
    records: list[Any],
    *,
    suffix_policy: dict[str, list[str]] | None = None,
) -> tuple[str, ...]:
    if suffix_policy is None:
        suffix_policy = policy_store.dependency_scope_profile("pipeline_run").get("optimizer", {})
    required: list[str] = []
    for record in records:
        profile = _optimizer_profile(record)
        if profile == "vision":
            _append_once(required, _OPTIMIZER_OCR_DEPENDENCY)
            continue
        if profile != "file":
            continue
        suffix = route_policy.normalized_suffix(_source_path(record))
        for dependency in suffix_policy.get(suffix, ()):
            _append_once(required, dependency)
    return tuple(required)


def optimizer_file_profile_required_dependencies(
    records: list[Any],
    *,
    suffix_policy: dict[str, list[str]] | None = None,
) -> tuple[str, ...]:
    if suffix_policy is None:
        suffix_policy = policy_store.dependency_scope_profile("pipeline_run").get("optimizer", {})
    required: list[str] = []
    for record in records:
        if _optimizer_profile(record) != "file":
            continue
        suffix = route_policy.normalized_suffix(_source_path(record))
        for dependency in suffix_policy.get(suffix, ()):
            if dependency not in required:
                required.append(dependency)
    return tuple(required)


def _append_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _source_path(record: Any) -> Path:
    return Path(
        str(
            getattr(record, "source_path", "")
            or getattr(record, "original_source_path", "")
            or getattr(record, "file_name", "")
        )
    )


def _optimizer_profile(record: Any) -> str:
    profile = str(getattr(record, "optimizer_profile", "")).strip().lower()
    if profile in {"vision", "file"}:
        return profile
    suffix = route_policy.normalized_suffix(_source_path(record))
    if suffix in route_policy.file_suffixes() or suffix == route_policy.pdf_suffix():
        return "file"
    if suffix in route_policy.image_suffixes():
        return "vision"
    return ""
