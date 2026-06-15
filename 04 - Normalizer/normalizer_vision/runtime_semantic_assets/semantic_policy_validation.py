"""Validation helpers for compiled semantic extraction guardrail policies."""
from __future__ import annotations

from typing import Any

_PROFILE_KEYS = frozenset(
    {
        "projection_id",
        "signals",
        "budgets",
        "allowed_section_roles",
        "allowed_synthetic_section_roles",
        "allowed_fact_families",
        "rescue_families",
        "table_compaction",
    }
)
_BUDGET_KEYS = frozenset({"max_sections", "max_section_chars", "max_facts", "max_tables", "max_table_rows"})
_RESOLUTION_KEYS = frozenset(
    {
        "min_score",
        "document_type_weight",
        "field_weight",
        "table_role_weight",
        "field_signal_limit",
        "table_signal_limit",
    }
)
_REQUIRED_SIGNAL_KEYS = frozenset({"document_types", "field_labels", "table_roles", "domains"})
_OPTIONAL_SIGNAL_LIST_KEYS = frozenset({"text_markers", "section_roles", "party_roles"})
_RESCUE_KEYS = frozenset({"document_header", "invoice_financial", "payment"})
_TABLE_KEYS = frozenset({"drop_text_only_rows", "max_rows_per_table"})


def validate_semantic_extraction_policy(policy: dict[str, Any], label: str) -> None:
    defaults = _require_dict(policy.get("defaults"), f"{label}.defaults")
    fallback_projection_id = _require_text(
        defaults.get("fallback_projection_id"),
        f"{label}.defaults.fallback_projection_id",
    )
    _validate_resolution(defaults.get("resolution"), f"{label}.defaults.resolution")
    _validate_profile(
        defaults.get("default_profile"),
        f"{label}.defaults.default_profile",
        expected_projection_id=fallback_projection_id,
    )
    overrides = _require_dict(policy.get("projection_overrides"), f"{label}.projection_overrides")
    for projection_id in sorted(overrides):
        _validate_profile(
            overrides.get(projection_id),
            f"{label}.projection_overrides[{projection_id}]",
            expected_projection_id=projection_id,
        )


def _validate_resolution(payload: Any, label: str) -> None:
    resolution = _require_dict(payload, label)
    missing = sorted(_RESOLUTION_KEYS - set(resolution))
    if missing:
        raise ValueError(f"{label} unvollstaendig: {', '.join(missing)}")
    for key in sorted(_RESOLUTION_KEYS):
        _require_int(resolution.get(key), f"{label}.{key}", minimum=1)


def _validate_profile(payload: Any, label: str, *, expected_projection_id: str) -> None:
    profile = _require_dict(payload, label)
    missing = sorted(_PROFILE_KEYS - set(profile))
    if missing:
        raise ValueError(f"{label} unvollstaendig: {', '.join(missing)}")
    if _require_text(profile.get("projection_id"), f"{label}.projection_id") != expected_projection_id:
        raise ValueError(f"{label}.projection_id passt nicht zum erwarteten Projection-Key.")
    signals = _require_dict(profile.get("signals"), f"{label}.signals")
    if sorted((_REQUIRED_SIGNAL_KEYS | _OPTIONAL_SIGNAL_LIST_KEYS | {"domain_markers"}) - set(signals)):
        raise ValueError(f"{label}.signals unvollstaendig.")
    for key in sorted(_REQUIRED_SIGNAL_KEYS):
        _require_text_list(signals.get(key), f"{label}.signals.{key}")
    for key in sorted(_OPTIONAL_SIGNAL_LIST_KEYS):
        _require_optional_text_list(signals.get(key), f"{label}.signals.{key}")
    _require_domain_markers(signals.get("domain_markers"), f"{label}.signals.domain_markers")
    budgets = _require_dict(profile.get("budgets"), f"{label}.budgets")
    missing_budgets = sorted(_BUDGET_KEYS - set(budgets))
    if missing_budgets:
        raise ValueError(f"{label}.budgets unvollstaendig: {', '.join(missing_budgets)}")
    for key in sorted(_BUDGET_KEYS):
        _require_int(budgets.get(key), f"{label}.budgets.{key}", minimum=1)
    _require_text_list(profile.get("allowed_section_roles"), f"{label}.allowed_section_roles")
    _require_text_list(profile.get("allowed_synthetic_section_roles"), f"{label}.allowed_synthetic_section_roles")
    _require_text_list(profile.get("allowed_fact_families"), f"{label}.allowed_fact_families")
    rescue_families = _require_dict(profile.get("rescue_families"), f"{label}.rescue_families")
    missing_rescues = sorted(_RESCUE_KEYS - set(rescue_families))
    if missing_rescues:
        raise ValueError(f"{label}.rescue_families unvollstaendig: {', '.join(missing_rescues)}")
    for key in sorted(_RESCUE_KEYS):
        _require_bool(rescue_families.get(key), f"{label}.rescue_families.{key}")
    table_compaction = _require_dict(profile.get("table_compaction"), f"{label}.table_compaction")
    missing_table = sorted(_TABLE_KEYS - set(table_compaction))
    if missing_table:
        raise ValueError(f"{label}.table_compaction unvollstaendig: {', '.join(missing_table)}")
    _require_bool(
        table_compaction.get("drop_text_only_rows"),
        f"{label}.table_compaction.drop_text_only_rows",
    )
    max_rows = _require_int(
        table_compaction.get("max_rows_per_table"),
        f"{label}.table_compaction.max_rows_per_table",
        minimum=1,
    )
    if max_rows > int(budgets.get("max_table_rows", 0) or 0):
        raise ValueError(f"{label}.table_compaction.max_rows_per_table darf max_table_rows nicht ueberschreiten.")


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return value


def _require_text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    result = [_require_text(item, f"{label}[]") for item in value]
    if not result:
        raise ValueError(f"{label} darf nicht leer sein.")
    return result


def _require_optional_text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    return [_require_text(item, f"{label}[]") for item in value]


def _require_domain_markers(value: Any, label: str) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    result: dict[str, list[str]] = {}
    for raw_key, raw_value in value.items():
        key = _require_text(raw_key, f"{label}.key")
        result[key] = _require_text_list(raw_value, f"{label}.{key}")
    return result


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return text


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return value


def _require_int(value: Any, label: str, *, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} fehlt oder ist ungueltig.") from None
    if parsed < minimum:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return parsed
