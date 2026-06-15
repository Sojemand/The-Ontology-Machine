"""Soft context promotion, heuristics, and review policy."""
from __future__ import annotations

import math
from typing import Any

from .domain import normalize_text
from .policy_context_aliases import (
    COUNTERPARTY_ALIASES,
    CURRENCY_ALIASES,
    DUE_ROW_HINTS,
    FIELD_ALIAS_MAP,
    GROSS_KEYS,
    BLOCKED_CONTEXT_KEYS,
    NET_KEYS,
    ROW_LABEL_KEYS,
    TAX_KEYS,
    TOTAL_ROW_HINTS,
)

def apply_context_policy(llm_result: dict[str, Any], request: dict[str, Any]) -> None:
    del request
    context = _ensure_mapping(llm_result, "context")
    content = _ensure_mapping(llm_result, "content")
    fields = _ensure_mapping(content, "fields")
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    for context_key, aliases in FIELD_ALIAS_MAP.items():
        _set_if_missing(context, context_key, _get_field_value(fields, aliases))
    total_row = _find_total_row(rows)
    if total_row:
        _set_if_missing(context, "net_amount", _row_value(total_row, NET_KEYS))
        _set_if_missing(context, "tax_amount", _row_value(total_row, TAX_KEYS))
    due_row = _find_due_row(rows)
    _set_if_missing(context, "total_monetary_value", _row_value(due_row or total_row or {}, GROSS_KEYS))
    if _missing(context, "currencies"):
        currencies = _normalize_currencies(_get_field_value(fields, CURRENCY_ALIASES))
        if currencies:
            context["currencies"] = currencies
    _set_if_missing(context, "counterparty", _pick_counterparty(context, fields))
    if _missing(context, "tax_rate"):
        net_amount = _coerce_number(context.get("net_amount"))
        tax_amount = _coerce_number(context.get("tax_amount"))
        if isinstance(net_amount, (int, float)) and isinstance(tax_amount, (int, float)) and net_amount > 0:
            context["tax_rate"] = round((tax_amount / net_amount) * 100, 2)
    _check_monetary_consistency(llm_result)
    for key in BLOCKED_CONTEXT_KEYS:
        context.pop(key, None)
    for key in [key for key, value in context.items() if value is None or value == "" or value == []]:
        del context[key]

def apply_review_reason(output: dict[str, Any], reason: str) -> None:
    processing = output.setdefault("processing", {})
    processing["needs_review"] = True
    if not processing.get("review_reason"):
        processing["review_reason"] = reason

def _ensure_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        value = {}
        payload[key] = value
    return value

def _set_if_missing(context: dict[str, Any], key: str, value: Any) -> None:
    if _missing(context, key) and _has_value(value):
        context[key] = value

def _missing(context: dict[str, Any], key: str) -> bool:
    return not _has_value(context.get(key))

def _get_field_value(fields: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        source_key = _lookup_alias_key(fields, alias)
        if source_key is not None and _has_value(fields[source_key]):
            return _extract_scalar(fields[source_key])
    return None


def _find_due_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((row for row in rows if isinstance(row, dict) and any(hint in _row_label(row) for hint in DUE_ROW_HINTS) and _row_value(row, GROSS_KEYS) is not None), None)


def _find_total_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = [(_row_score(row, len(rows)), row) for row in rows if isinstance(row, dict) and _row_label(row)]
    ranked = [(score, row) for score, row in ranked if score > 0]
    return max(ranked, default=(0, None), key=lambda item: item[0])[1]


def _row_score(row: dict[str, Any], row_count: int) -> int:
    label = _row_label(row)
    has_total_hint = any(hint in label for hint in TOTAL_ROW_HINTS)
    if not has_total_hint and row_count > 1:
        return 0
    return int(has_total_hint) * 3 + int(_row_value(row, NET_KEYS) is not None) + int(_row_value(row, TAX_KEYS) is not None) + int(_row_value(row, GROSS_KEYS) is not None)


def _check_monetary_consistency(llm_result: dict[str, Any]) -> None:
    context = llm_result.get("context", {})
    net = _coerce_number(context.get("net_amount"))
    tax = _coerce_number(context.get("tax_amount"))
    gross = _coerce_number(context.get("total_monetary_value"))
    if isinstance(net, (int, float)) and isinstance(gross, (int, float)) and net > 0 and gross > 0 and net > gross:
        apply_review_reason(llm_result, "net_amount > total_monetary_value - vermutlich Erfassungsfehler.")
    if all(isinstance(value, (int, float)) for value in (net, tax, gross)) and net > 0 and gross > 0:
        if abs((net + tax) - gross) / gross > 0.05:
            apply_review_reason(llm_result, "net + tax weicht > 5% von gross ab - Werte pruefen.")


def _pick_counterparty(context: dict[str, Any], fields: dict[str, Any]) -> Any:
    company = context.get("company")
    for candidate in (context.get("counterparty"), context.get("recipient_name"), _get_field_value(fields, COUNTERPARTY_ALIASES)):
        if _has_value(candidate) and not _same_normalized_text(candidate, company):
            return candidate
    return None


def _extract_scalar(value: Any) -> Any:
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def _has_value(value: Any) -> bool:
    scalar = _extract_scalar(value)
    if scalar is None:
        return False
    if isinstance(scalar, str):
        return bool(scalar.strip())
    if isinstance(scalar, (list, dict)):
        return bool(scalar)
    return True


def _coerce_number(value: Any) -> float | int | None:
    scalar = _extract_scalar(value)
    if isinstance(scalar, bool) or not _has_value(scalar):
        return None
    if isinstance(scalar, (int, float)):
        return scalar if math.isfinite(float(scalar)) else None
    text = str(scalar).strip().replace("EUR", "").replace("eur", "").replace("Ã¢â€šÂ¬", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def _lookup_alias_key(mapping: dict[str, Any], alias: str) -> str | None:
    lowered = {str(key).lower(): key for key in mapping}
    return lowered.get(alias.lower())


def _row_label(row: dict[str, Any]) -> str:
    parts = [normalize_text(_extract_scalar(row.get(key))) for key in ROW_LABEL_KEYS if key in row and _has_value(row.get(key))]
    return " ".join(part for part in parts if part).lower()


def _row_value(row: dict[str, Any], aliases: tuple[str, ...]) -> float | int | None:
    for alias in aliases:
        source_key = _lookup_alias_key(row, alias)
        if source_key is not None:
            number = _coerce_number(row.get(source_key))
            if number is not None:
                return number
    return None


def _same_normalized_text(left: Any, right: Any) -> bool:
    return _has_value(left) and _has_value(right) and normalize_text(left).lower() == normalize_text(right).lower()


def _normalize_currencies(value: Any) -> list[str]:
    scalar = _extract_scalar(value)
    items = scalar if isinstance(scalar, list) else [scalar]
    result: list[str] = []
    for item in items:
        currency = normalize_text(item).upper()
        if currency and currency not in result:
            result.append(currency)
    return result
