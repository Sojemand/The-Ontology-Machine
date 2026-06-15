"""Pure row-level normalization logic for normalized outputs."""
from __future__ import annotations

from typing import Any

from ..models.coercion import coerce_int
from ..models.serialization import to_json_compatible
from ..taxonomy import TaxonomyProfile
from . import policy

ROW_META_KEYS = {"_row_type", "_row_index", "_source_refs", "_units"}
DATE_CELL_CODES = {"scheduled_date"}


def normalize_rows(
    profile: TaxonomyProfile,
    parsed_rows: Any,
    notes: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(parsed_rows, list):
        return []

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(parsed_rows):
        if not isinstance(row, dict):
            continue
        normalized_row = _normalize_single_row(profile, row, index, notes)
        for expanded_row in _expand_row_lists(normalized_row):
            expanded_row["_row_index"] = len(rows)
            if any(key not in {"_row_type", "_row_index"} for key in expanded_row):
                rows.append(expanded_row)
    return rows


def _normalize_single_row(
    profile: TaxonomyProfile,
    row: dict[str, Any],
    index: int,
    notes: list[str],
) -> dict[str, Any]:
    normalized_row: dict[str, Any] = {
        "_row_type": profile.canonical_code("row", row.get("_row_type"), "other"),
        "_row_index": coerce_int(row.get("_row_index"), index),
    }
    extra: dict[str, Any] = {}
    units_in = row.get("_units", {}) if isinstance(row.get("_units"), dict) else {}
    units_out: dict[str, str] = {}
    for key, value in row.items():
        if key in ROW_META_KEYS:
            continue
        canonical = profile.canonical_code("cell", key, None)
        if canonical is None:
            extra[str(key)] = policy.normalize_output_value(value)
            continue
        if policy.is_empty_placeholder(value):
            continue
        normalized_row[canonical] = _normalize_cell_value(canonical, value)
        unit_value = units_in.get(key, units_in.get(canonical))
        if isinstance(unit_value, str) and unit_value.strip():
            units_out[canonical] = unit_value.strip()
    if extra:
        notes.append(f"Dropped unknown cell codes in row {index}: {', '.join(sorted(extra))}.")
        if "other" in profile.cell_codes:
            normalized_row["other"] = extra
    normalized_row = _postprocess_row(normalized_row)
    if units_out:
        normalized_row["_units"] = units_out
    return normalized_row


def _postprocess_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized_row = dict(row)
    if normalized_row.get("_row_type") != "payment_schedule":
        return normalized_row
    line_total = normalized_row.get("line_total")
    amount_due = normalized_row.get("amount_due")
    if line_total is None or amount_due is None or line_total == amount_due:
        return normalized_row
    if policy.has_tax_split_hint(normalized_row):
        normalized_row["amount_due"] = line_total
    return normalized_row


def _expand_row_lists(row: dict[str, Any]) -> list[dict[str, Any]]:
    list_keys = [key for key, value in row.items() if key not in ROW_META_KEYS and isinstance(value, list)]
    if not list_keys:
        return [row]

    max_len = max((len(row[key]) for key in list_keys), default=0)
    if max_len <= 0:
        return [{key: value for key, value in row.items() if key not in list_keys}]

    expanded_rows: list[dict[str, Any]] = []
    for offset in range(max_len):
        expanded_row: dict[str, Any] = {}
        for key, value in row.items():
            if key == "_units" and isinstance(value, dict):
                expanded_row[key] = dict(value)
                continue
            if key in ROW_META_KEYS:
                expanded_row[key] = value
                continue
            if key not in list_keys:
                expanded_row[key] = value
                continue
            normalized_item = _normalize_list_item_value(key, value[offset] if offset < len(value) else None)
            if policy.is_empty_placeholder(normalized_item):
                if "_units" in expanded_row and isinstance(expanded_row["_units"], dict):
                    expanded_row["_units"].pop(key, None)
                continue
            expanded_row[key] = normalized_item
        if "_units" in expanded_row and isinstance(expanded_row["_units"], dict) and not expanded_row["_units"]:
            expanded_row.pop("_units")
        expanded_rows.append(expanded_row)
    return expanded_rows


def _normalize_list_item_value(key: str, value: Any) -> Any:
    normalized = _normalize_cell_value(key, value)
    if isinstance(normalized, (list, dict)):
        flattened = policy.collapse_whitespace(" ".join(policy.flatten_tokens(normalized)))
        return flattened or None
    return normalized


def _normalize_cell_value(key: str, value: Any) -> Any:
    if key in DATE_CELL_CODES:
        return to_json_compatible(policy.normalize_iso_date(value))
    return policy.normalize_output_value(value)
