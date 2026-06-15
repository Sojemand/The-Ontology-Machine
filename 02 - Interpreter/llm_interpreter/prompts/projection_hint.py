"""Projection-hint prompt text and contract validation helpers."""
from __future__ import annotations

import math
from typing import Any

_CATALOG_HEADER = (
    "Projection routing catalog. Choose exactly one projection_id from this list "
    "when clearly applicable; otherwise leave projection_hint empty:"
)
_OPTIONAL_CATALOG_METADATA_FIELDS = (
    "release_id",
    "release_version",
    "release_fingerprint",
    "master_taxonomy_id",
    "master_taxonomy_release_id",
    "runtime_locale",
)


def build_projection_catalog_block(request: dict[str, Any]) -> str:
    catalog = require_projection_catalog(request.get("projection_catalog"), error_type=ValueError)
    lines = [_CATALOG_HEADER]
    control_locale = str(catalog.get("runtime_locale") or "").strip()
    if control_locale:
        lines.append(
            f"Control locale: {control_locale}. Map semantic classification labels, routing decisions, "
            "field/row key names, and projection_hint.matched_signals into this catalog language. "
            "Preserve document values and content.free_text in the source language."
        )
    for entry in catalog["projections"]:
        example_document_types = ", ".join(entry["example_document_types"])
        lines.append(
            "projection_id="
            f"{entry['projection_id']} | label={entry['label']} | when_to_use={entry['when_to_use']} | "
            f"avoid_when={entry['avoid_when']} | example_document_types={example_document_types}"
        )
    return "\n".join(lines)


def validate_projection_catalog(catalog: Any, *, error_type: type[Exception]) -> None:
    require_projection_catalog(catalog, error_type=error_type)


def require_projection_catalog(catalog: Any, *, error_type: type[Exception]) -> dict[str, Any]:
    normalized = coerce_projection_catalog(catalog)
    if normalized is not None:
        return normalized
    if catalog is None:
        raise error_type("projection_catalog fehlt")
    raise error_type("projection_catalog ist ungueltig")


def validate_projection_hint(
    context: dict[str, Any],
    request: dict[str, Any],
    *,
    error_type: type[Exception],
) -> None:
    hint = context.get("projection_hint")
    if hint is None:
        return
    if not isinstance(hint, dict):
        raise error_type("LLM-Output ungueltig: context.projection_hint muss ein Objekt sein")
    projection_id = hint.get("projection_id")
    if projection_id is not None and not isinstance(projection_id, str):
        raise error_type("LLM-Output ungueltig: context.projection_hint.projection_id muss str oder null sein")
    reason = hint.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise error_type("LLM-Output ungueltig: context.projection_hint.reason muss str oder null sein")
    matched_signals = hint.get("matched_signals", [])
    if matched_signals is None:
        matched_signals = []
    if not isinstance(matched_signals, list) or any(not isinstance(item, str) for item in matched_signals):
        raise error_type("LLM-Output ungueltig: context.projection_hint.matched_signals muss string[] sein")
    hint["matched_signals"] = matched_signals
    projection_id = str(projection_id).strip() if isinstance(projection_id, str) else None
    has_reason = bool(str(reason or "").strip())
    has_signals = any(str(item).strip() for item in matched_signals)
    confidence = _coerce_projection_hint_confidence(hint.get("confidence"))
    if confidence is None:
        if projection_id or has_reason or has_signals:
            raise error_type("LLM-Output ungueltig: context.projection_hint.confidence muss number sein")
        hint["confidence"] = 0.0
    else:
        hint["confidence"] = confidence
    if not projection_id:
        return
    catalog = coerce_projection_catalog(request.get("projection_catalog"))
    if catalog is None:
        raise error_type("LLM-Output ungueltig: projection_hint.projection_id erfordert projection_catalog im Request")
    allowed_ids = {entry["projection_id"] for entry in catalog["projections"]}
    if projection_id not in allowed_ids:
        raise error_type("LLM-Output ungueltig: context.projection_hint.projection_id ist nicht im projection_catalog")


def prune_empty_projection_hint(context: dict[str, Any]) -> None:
    hint = context.get("projection_hint")
    if not isinstance(hint, dict):
        return
    projection_id = str(hint.get("projection_id") or "").strip()
    reason = str(hint.get("reason") or "").strip()
    matched_signals = hint.get("matched_signals")
    if projection_id:
        return
    if reason:
        return
    if isinstance(matched_signals, list) and any(str(item).strip() for item in matched_signals):
        return
    context.pop("projection_hint", None)


def _coerce_projection_hint_confidence(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value if math.isfinite(float(value)) else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    normalized = text.replace(",", ".")
    try:
        number = float(normalized)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def coerce_projection_catalog(catalog: Any) -> dict[str, Any] | None:
    if catalog is None:
        return None
    if not isinstance(catalog, dict):
        return None
    catalog_version = str(catalog.get("catalog_version") or "").strip()
    master_taxonomy_version = str(catalog.get("master_taxonomy_version") or "").strip()
    projections = catalog.get("projections")
    if not catalog_version or not master_taxonomy_version or not isinstance(projections, list):
        return None
    normalized_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in projections:
        if not isinstance(item, dict):
            return None
        projection_id = str(item.get("projection_id") or "").strip()
        label = str(item.get("label") or "").strip()
        when_to_use = str(item.get("when_to_use") or "").strip()
        avoid_when = str(item.get("avoid_when") or "").strip()
        examples = item.get("example_document_types")
        if not projection_id or not label or not when_to_use or not avoid_when or not isinstance(examples, list):
            return None
        example_document_types = [str(value).strip() for value in examples if str(value).strip()]
        if len(example_document_types) != len(examples) or projection_id in seen_ids:
            return None
        seen_ids.add(projection_id)
        normalized_entries.append(
            {
                "projection_id": projection_id,
                "label": label,
                "when_to_use": when_to_use,
                "avoid_when": avoid_when,
                "example_document_types": example_document_types,
            }
        )
    normalized_catalog = {
        "catalog_version": catalog_version,
        "master_taxonomy_version": master_taxonomy_version,
        "projections": normalized_entries,
    }
    for field in _OPTIONAL_CATALOG_METADATA_FIELDS:
        if field not in catalog:
            continue
        value = str(catalog.get(field) or "").strip()
        if not value:
            return None
        if field == "runtime_locale" and value != "en":
            return None
        normalized_catalog[field] = value
    return normalized_catalog


__all__ = [
    "build_projection_catalog_block",
    "coerce_projection_catalog",
    "prune_empty_projection_hint",
    "require_projection_catalog",
    "validate_projection_catalog",
    "validate_projection_hint",
]
