"""Advisory projection-hint normalization for the live vision workflow."""
from __future__ import annotations

import math
from typing import Any

from ..prompts.projection_hint import coerce_projection_catalog


def normalize_projection_hint(llm_result: dict[str, Any], request: dict[str, Any]) -> None:
    context = llm_result.get("context")
    if not isinstance(context, dict):
        return
    if "projection_hint" not in context:
        return
    normalized = _normalize_hint(context.get("projection_hint"), request)
    if normalized is None:
        context.pop("projection_hint", None)
        return
    context["projection_hint"] = normalized


def _normalize_hint(hint: Any, request: dict[str, Any]) -> dict[str, Any] | None:
    if hint is None or not isinstance(hint, dict):
        return None
    projection_id = _clean_text(hint.get("projection_id"))
    if not projection_id:
        return None
    if projection_id not in _allowed_projection_ids(request):
        return None
    return {
        "projection_id": projection_id,
        "confidence": _coerce_confidence(hint.get("confidence")),
        "reason": _clean_text(hint.get("reason")) or None,
        "matched_signals": _clean_signal_list(hint.get("matched_signals")),
    }


def _allowed_projection_ids(request: dict[str, Any]) -> set[str]:
    catalog = coerce_projection_catalog(request.get("projection_catalog"))
    if catalog is None:
        return set()
    return {entry["projection_id"] for entry in catalog["projections"]}


def _clean_signal_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            result.append(text)
    return result


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _coerce_confidence(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else 0.0
    text = str(value).strip().replace(",", ".")
    if not text:
        return 0.0
    try:
        number = float(text)
    except ValueError:
        return 0.0
    return number if math.isfinite(number) else 0.0


__all__ = ["normalize_projection_hint"]
