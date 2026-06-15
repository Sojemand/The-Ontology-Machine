"""Config types and validation for the self-contained vision validator."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..paths import default_config_path, ensure_app_layout

VALID_LEVELS = {"FAIL", "WARN"}


def resolve_config_path(config_path: str | Path | None = None, *, root: Path | None = None) -> Path:
    if config_path is None or str(config_path).strip() == "":
        return default_config_path(root)
    return Path(config_path)


@dataclass
class CheckToggles:
    free_text: bool = True
    context_scalars: bool = True
    content_fields: bool = True
    rows: bool = True


@dataclass
class MatchConfig:
    scalar_level: str = "FAIL"
    row_level: str = "WARN"
    require_free_text: bool = True
    number_tolerance_absolute: float = 0.01
    min_string_length: int = 4
    min_compact_length: int = 5
    context_fields: list[str] = field(default_factory=lambda: [
        "company", "document_date", "document_title", "total_monetary_value", "total_hours",
        "tax_amount", "net_amount", "reference_number", "due_date", "counterparty",
        "opening_balance", "closing_balance", "document_number", "recipient_name",
        "customer_number",
    ])
    skip_content_fields: list[str] = field(default_factory=lambda: ["_source_refs"])
    skip_row_fields: list[str] = field(default_factory=lambda: ["_source_refs", "page", "sequence", "confidence"])
    row_anchor_keys: list[str] = field(default_factory=lambda: [
        "position",
        "description",
        "label",
        "item",
        "title",
        "name",
        "question",
        "text",
        "content",
        "value",
        "summary",
    ])


@dataclass
class ValidatorConfig:
    checks: CheckToggles = field(default_factory=CheckToggles)
    match: MatchConfig = field(default_factory=MatchConfig)
    flag_needs_review: bool = True
    max_issues_per_check: int = 20


def _validate_config(cfg: ValidatorConfig) -> None:
    errors: list[str] = []
    if cfg.match.scalar_level not in VALID_LEVELS:
        errors.append("match.scalar_level muss FAIL oder WARN sein")
    if cfg.match.row_level not in VALID_LEVELS:
        errors.append("match.row_level muss FAIL oder WARN sein")
    if cfg.match.number_tolerance_absolute < 0:
        errors.append("match.number_tolerance_absolute muss >= 0 sein")
    if cfg.match.min_string_length < 1:
        errors.append("match.min_string_length muss >= 1 sein")
    if cfg.match.min_compact_length < 1:
        errors.append("match.min_compact_length muss >= 1 sein")
    if cfg.max_issues_per_check < 1:
        errors.append("max_issues_per_check muss >= 1 sein")
    if errors:
        raise ValueError("Ungueltige Validator-Config:\n  " + "\n  ".join(errors))


def _require_object(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} muss ein JSON-Objekt sein")
    return value


def _require_bool(value: Any, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} muss true oder false sein")
    return value


def _require_float(value: Any, *, field_name: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} muss eine Zahl sein")
    return float(value)


def _require_int(value: Any, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} muss eine Ganzzahl sein")
    return value


def _require_string(value: Any, *, field_name: str, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{field_name} muss ein String sein")
    return value


def _require_string_list(value: Any, *, field_name: str, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} muss eine Liste von Strings sein")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{field_name}[{index}] muss ein String sein")
        stripped = item.strip()
        if stripped:
            result.append(stripped)
    return result


def load_config(config_path: str | Path | None = None) -> ValidatorConfig:
    defaults = ValidatorConfig()
    explicit_config = config_path is not None and str(config_path).strip() != ""
    if explicit_config:
        path = resolve_config_path(config_path)
    else:
        path = default_config_path(ensure_app_layout())
    if not path.exists():
        if explicit_config:
            raise ValueError(f"Config nicht gefunden: {path}")
        return defaults

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config ist kein gueltiges JSON: {path} ({exc})") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Config ist kein JSON-Objekt: {path}")

    checks = _require_object(raw.get("checks"), field_name="checks")
    match = _require_object(raw.get("match"), field_name="match")
    cfg = ValidatorConfig(
        checks=CheckToggles(
            free_text=_require_bool(checks.get("free_text"), field_name="checks.free_text", default=True),
            context_scalars=_require_bool(checks.get("context_scalars"), field_name="checks.context_scalars", default=True),
            content_fields=_require_bool(checks.get("content_fields"), field_name="checks.content_fields", default=True),
            rows=_require_bool(checks.get("rows"), field_name="checks.rows", default=True),
        ),
        match=MatchConfig(
            scalar_level=_require_string(match.get("scalar_level"), field_name="match.scalar_level", default="FAIL"),
            row_level=_require_string(match.get("row_level"), field_name="match.row_level", default="WARN"),
            require_free_text=_require_bool(match.get("require_free_text"), field_name="match.require_free_text", default=True),
            number_tolerance_absolute=_require_float(match.get("number_tolerance_absolute"), field_name="match.number_tolerance_absolute", default=defaults.match.number_tolerance_absolute),
            min_string_length=_require_int(match.get("min_string_length"), field_name="match.min_string_length", default=defaults.match.min_string_length),
            min_compact_length=_require_int(match.get("min_compact_length"), field_name="match.min_compact_length", default=defaults.match.min_compact_length),
            context_fields=_require_string_list(match.get("context_fields"), field_name="match.context_fields", default=defaults.match.context_fields),
            skip_content_fields=_require_string_list(match.get("skip_content_fields"), field_name="match.skip_content_fields", default=defaults.match.skip_content_fields),
            skip_row_fields=_require_string_list(match.get("skip_row_fields"), field_name="match.skip_row_fields", default=defaults.match.skip_row_fields),
            row_anchor_keys=_require_string_list(match.get("row_anchor_keys"), field_name="match.row_anchor_keys", default=defaults.match.row_anchor_keys),
        ),
        flag_needs_review=_require_bool(raw.get("flag_needs_review"), field_name="flag_needs_review", default=defaults.flag_needs_review),
        max_issues_per_check=_require_int(raw.get("max_issues_per_check"), field_name="max_issues_per_check", default=defaults.max_issues_per_check),
    )
    _validate_config(cfg)
    return cfg
