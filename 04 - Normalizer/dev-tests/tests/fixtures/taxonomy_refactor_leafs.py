from __future__ import annotations

from typing import Any

from tests.fixtures.taxonomy_refactor_classification import (
    classify_path,
    inventory_location_key_for,
    inventory_location_value_for,
)
from tests.fixtures.taxonomy_refactor_io import canonical_sha256
from tests.fixtures.taxonomy_refactor_paths import CORE_CLASSIFICATIONS


def core_leaf_values(payload: Any, *, artifact_kind: str, projection_id: str | None = None) -> dict[str, list[Any]]:
    return comparable_leaf_values(
        payload,
        artifact_kind=artifact_kind,
        projection_id=projection_id,
        allowed_classifications=CORE_CLASSIFICATIONS,
    )


def comparable_leaf_values(
    payload: Any,
    *,
    artifact_kind: str,
    projection_id: str | None = None,
    allowed_classifications: frozenset[str] = CORE_CLASSIFICATIONS,
) -> dict[str, list[Any]]:
    observed: dict[str, list[Any]] = {}
    _collect_leaf_values(payload, "$", observed)
    return {
        json_path: values
        for json_path, values in sorted(observed.items())
        if classify_path(artifact_kind, json_path) in allowed_classifications
    }


def comparable_snapshot_fingerprint(
    payload: Any,
    *,
    artifact_kind: str,
    projection_id: str | None = None,
    allowed_classifications: frozenset[str] = CORE_CLASSIFICATIONS,
) -> str:
    return canonical_sha256(
        comparable_leaf_values(
            payload,
            artifact_kind=artifact_kind,
            projection_id=projection_id,
            allowed_classifications=allowed_classifications,
        )
    )


def build_inventory_entries(payload: Any, *, artifact_kind: str, projection_id: str | None = None) -> list[dict[str, str]]:
    observed: dict[str, set[str]] = {}
    _collect_leaf_kinds(payload, "$", observed)
    entries: list[dict[str, str]] = []
    location_key = inventory_location_key_for(artifact_kind)
    for json_path in sorted(observed):
        classification = classify_path(artifact_kind, json_path)
        entry = {
            "artifact_kind": artifact_kind,
            "json_path": json_path,
            "value_kind": "|".join(sorted(observed[json_path])),
            "classification": classification,
        }
        entry[location_key] = inventory_location_value_for(artifact_kind, classification, projection_id=projection_id)
        entries.append(entry)
    return entries


def _collect_leaf_kinds(value: Any, json_path: str, observed: dict[str, set[str]]) -> None:
    if isinstance(value, dict):
        if not value:
            _record_kind(observed, json_path, "empty_object")
            return
        for key in sorted(value):
            _collect_leaf_kinds(value[key], f"{json_path}.{key}", observed)
        return
    if isinstance(value, list):
        _collect_list_leaf_kinds(value, json_path, observed)
        return
    _record_kind(observed, json_path, _scalar_kind(value))


def _collect_list_leaf_kinds(value: list[Any], json_path: str, observed: dict[str, set[str]]) -> None:
    if not value:
        _record_kind(observed, json_path, "empty_list")
        return
    has_containers = any(isinstance(item, (dict, list)) for item in value)
    has_scalars = any(not isinstance(item, (dict, list)) for item in value)
    if has_containers and has_scalars:
        raise ValueError(f"Gemischte Listentypen werden nicht unterstuetzt: {json_path}")
    if has_scalars:
        for item in value:
            _record_kind(observed, f"{json_path}[]", _scalar_kind(item))
        return
    for item in value:
        _collect_leaf_kinds(item, f"{json_path}[]", observed)


def _record_kind(observed: dict[str, set[str]], json_path: str, kind: str) -> None:
    observed.setdefault(json_path, set()).add(kind)


def _scalar_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "string"


def _collect_leaf_values(value: Any, json_path: str, observed: dict[str, list[Any]]) -> None:
    if isinstance(value, dict):
        if not value:
            _record_leaf_value(observed, json_path, "__empty_object__")
            return
        for key in sorted(value):
            _collect_leaf_values(value[key], f"{json_path}.{key}", observed)
        return
    if isinstance(value, list):
        _collect_list_leaf_values(value, json_path, observed)
        return
    _record_leaf_value(observed, json_path, value)


def _collect_list_leaf_values(value: list[Any], json_path: str, observed: dict[str, list[Any]]) -> None:
    if not value:
        _record_leaf_value(observed, json_path, "__empty_list__")
        return
    has_containers = any(isinstance(item, (dict, list)) for item in value)
    has_scalars = any(not isinstance(item, (dict, list)) for item in value)
    if has_containers and has_scalars:
        raise ValueError(f"Gemischte Listentypen werden nicht unterstuetzt: {json_path}")
    if has_scalars:
        for item in value:
            _record_leaf_value(observed, f"{json_path}[]", item)
        return
    for item in value:
        _collect_leaf_values(item, f"{json_path}[]", observed)


def _record_leaf_value(observed: dict[str, list[Any]], json_path: str, value: Any) -> None:
    observed.setdefault(json_path, []).append(value)
