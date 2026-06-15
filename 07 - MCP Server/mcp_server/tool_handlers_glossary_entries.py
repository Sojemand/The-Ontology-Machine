from __future__ import annotations

from pathlib import Path
from typing import Any

from .tool_handler_contracts import _workspace_normalizer_home
from .tool_handler_types import ToolFailure


def response(
    *,
    operation: str,
    locale: str,
    entries: list[dict[str, Any]],
    available_locales: list[str],
    artifact_path: Path | None,
    entry_status: str,
    english_term: str = "",
) -> dict[str, Any]:
    return {
        "status": "ok",
        "operation": operation,
        "locale": locale,
        "available_locales": available_locales,
        "entry_count": len(entries),
        "entries": sorted_entries(entries),
        "entry_status": entry_status,
        "english_term": english_term,
        "authoring_scope": "workspace" if artifact_path else "global",
        "artifact_folder": str(artifact_path) if artifact_path else "",
        "normalizer_authoring_home": str(_workspace_normalizer_home(artifact_path)) if artifact_path else "",
        "glossary_exists": bool(entries),
    }


def response_entries(result: dict[str, Any], *, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    value = result.get("value")
    if not isinstance(value, dict):
        return sorted_entries(fallback)
    entries = value.get("entries")
    if not isinstance(entries, list):
        return sorted_entries(fallback)
    cleaned = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        try:
            cleaned.append(
                {
                    "english_term": require_clean_text(raw.get("english_term"), label="english_term"),
                    "canonical": require_clean_text(raw.get("canonical"), label="canonical"),
                    "aliases": dedupe_strings(require_clean_string_list(raw.get("aliases"), label="aliases")),
                }
            )
        except ToolFailure:
            continue
    return sorted_entries(cleaned or fallback)


def require_clean_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolFailure(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()


def require_clean_string_list(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ToolFailure(f"{label} muss eine String-Liste sein.")
    return [require_clean_text(item, label=label) for item in value]


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def sorted_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (
            {
                "english_term": require_clean_text(item.get("english_term"), label="english_term"),
                "canonical": require_clean_text(item.get("canonical"), label="canonical"),
                "aliases": dedupe_strings(require_clean_string_list(item.get("aliases"), label="aliases")),
            }
            for item in entries
        ),
        key=lambda item: item["english_term"].casefold(),
    )


__all__ = [
    "dedupe_strings",
    "response",
    "response_entries",
    "sorted_entries",
]
