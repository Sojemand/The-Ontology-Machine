from __future__ import annotations

from .tool_handler_deps import *


def release_summary(payload: dict[str, Any] | None, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    fallback = fallback if isinstance(fallback, dict) else {}
    projection_ids = payload.get("projection_ids")
    if not isinstance(projection_ids, list):
        projection_ids = fallback.get("projection_ids")
    return {
        "release_id": _summary_value(payload, fallback, "release_id"),
        "release_version": _summary_value(payload, fallback, "release_version"),
        "fingerprint": _summary_value(payload, fallback, "fingerprint"),
        "master_taxonomy_id": _summary_value(payload, fallback, "master_taxonomy_id"),
        "master_taxonomy_release_id": _summary_value(payload, fallback, "master_taxonomy_release_id"),
        "runtime_locale": _summary_value(payload, fallback, "runtime_locale") or _summary_value(payload, fallback, "locale"),
        "projection_ids": [str(item).strip() for item in (projection_ids or []) if str(item).strip()],
    }


def active_release_summary(
    active_release_payload: dict[str, Any] | None,
    semantic_status: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = active_release_payload if isinstance(active_release_payload, dict) else {}
    release = payload.get("release") if isinstance(payload.get("release"), dict) else {}
    detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
    if not release and isinstance(detail.get("release"), dict):
        release = detail["release"]
    status = semantic_status if isinstance(semantic_status, dict) else {}
    if isinstance(status.get("status"), dict):
        status = status["status"]
    return {
        "release_id": _first_text(release.get("release_id"), payload.get("release_id"), status.get("active_release_id")),
        "release_version": _first_text(
            release.get("release_version"),
            payload.get("release_version"),
            status.get("active_release_version"),
        ),
        "fingerprint": _first_text(
            release.get("fingerprint"),
            payload.get("fingerprint"),
            status.get("active_release_fingerprint"),
        ),
        "master_taxonomy_id": _first_text(release.get("master_taxonomy_id")),
        "master_taxonomy_release_id": _first_text(
            release.get("master_taxonomy_release_id"),
            payload.get("master_taxonomy_release_id"),
            status.get("active_master_taxonomy_release_id"),
        ),
        "runtime_locale": _first_text(
            release.get("runtime_locale"),
            payload.get("runtime_locale"),
            status.get("active_runtime_locale"),
        ),
        "projection_ids": _summary_projection_ids(release, payload),
    }


def _summary_value(payload: dict[str, Any], fallback: dict[str, Any], key: str) -> str | None:
    value = str(payload.get(key) or fallback.get(key) or "").strip()
    return value or None


def _summary_projection_ids(release: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    for candidate in (release.get("projection_ids"), payload.get("projection_ids")):
        if isinstance(candidate, list):
            return [str(item).strip() for item in candidate if str(item).strip()]
    return []


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


__all__ = [name for name in globals() if not name.startswith("__")]
