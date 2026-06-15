"""Pure domain helpers for release projection expansion."""
from __future__ import annotations

from typing import Any


def materialize_projection(release: dict[str, Any], projection_id: str) -> dict[str, Any]:
    master = release.get("master_taxonomy", {})
    projections = release.get("projections", [])
    selected = next(
        (
            projection
            for projection in projections
            if isinstance(projection, dict) and str(projection.get("projection_id") or "").strip() == projection_id
        ),
        None,
    )
    if selected is None:
        raise ValueError(f"Projection im aktiven Release nicht gefunden: {projection_id}")
    section_indexes = {
        "document_types": _master_index(master, "document_types", "code"),
        "categories": _master_index(master, "categories", "code"),
        "subcategories": _master_index(master, "subcategories", "code"),
        "field_codes": _master_index(master, "field_codes", "code"),
        "row_types": _master_index(master, "row_types", "code"),
        "cell_codes": _master_index(master, "cell_codes", "code"),
    }
    materialized = dict(selected)
    materialized["promotion_slots"] = list(master.get("promotion_slots", []) or [])
    for section_key, include_key in (
        ("document_types", "include_document_types"),
        ("categories", "include_categories"),
        ("subcategories", "include_subcategories"),
        ("field_codes", "include_field_codes"),
        ("row_types", "include_row_types"),
        ("cell_codes", "include_cell_codes"),
    ):
        codes = selected.get(include_key, []) or []
        materialized[section_key] = [
            section_indexes[section_key][code]
            for code in codes
            if code in section_indexes[section_key]
        ]
    return materialized


def _master_index(master: dict[str, Any], section_key: str, code_key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in master.get(section_key, []) or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get(code_key) or "").strip()
        if code:
            indexed[code] = item
    return indexed
