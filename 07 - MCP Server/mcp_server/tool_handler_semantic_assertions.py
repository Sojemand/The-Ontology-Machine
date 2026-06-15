from __future__ import annotations

import json
from typing import Any

from .tool_handler_types import ToolFailure

def _status_label(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "").strip().casefold()
    if status in {"ok", "success", "applied", "ready", "valid"}:
        return "ok"
    if status:
        return status
    return "unknown"


def _assert_semantic_release_selection(
    payload: dict[str, Any],
    *,
    expected_language: str,
    expected_projection_ids: list[str],
    source_label: str,
) -> dict[str, Any]:
    detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
    release = payload.get("release") if isinstance(payload.get("release"), dict) else {}
    if not release and isinstance(detail.get("release"), dict):
        release = detail["release"]
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    if not status and isinstance(detail.get("status"), dict):
        status = detail["status"]
    runtime_locale = str(
        release.get("runtime_locale")
        or payload.get("runtime_locale")
        or detail.get("runtime_locale")
        or status.get("active_runtime_locale")
        or ""
    ).strip()
    projection_ids = _semantic_projection_ids(payload, release)
    expected_projection_ids = [item.strip() for item in expected_projection_ids if item.strip()]
    if expected_language and not runtime_locale:
        raise ToolFailure(f"{source_label} konnte runtime_locale nach der Aktivierung nicht verifizieren.")
    if expected_projection_ids and not projection_ids:
        raise ToolFailure(f"{source_label} konnte Projection-Liste nach der Aktivierung nicht verifizieren.")
    if runtime_locale and runtime_locale != expected_language:
        raise ToolFailure(
            f"{source_label} verwendet runtime_locale '{runtime_locale}', erwartet war '{expected_language}'."
        )
    if expected_projection_ids and projection_ids and projection_ids != expected_projection_ids:
        raise ToolFailure(
            f"{source_label} verwendet Projection-Liste {projection_ids}, erwartet war {expected_projection_ids}."
        )
    return {
        "verified": bool(runtime_locale or projection_ids),
        "runtime_locale": runtime_locale or None,
        "projection_ids": projection_ids,
        "expected_runtime_locale": expected_language,
        "expected_projection_ids": expected_projection_ids,
    }


def _semantic_projection_ids(payload: dict[str, Any], release: dict[str, Any]) -> list[str]:
    detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
    candidates = (
        release.get("projection_ids"),
        payload.get("projection_ids"),
        detail.get("projection_ids"),
        (payload.get("value") or {}).get("projection_ids") if isinstance(payload.get("value"), dict) else None,
    )
    for candidate in candidates:
        if isinstance(candidate, list) and all(isinstance(item, str) for item in candidate):
            return [item.strip() for item in candidate if item.strip()]
    return []

__all__ = [name for name in globals() if not name.startswith("__")]
