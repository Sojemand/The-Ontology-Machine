from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .tool_handler_deps import *
from .tool_handlers_glossary_entries import dedupe_strings, response, response_entries, sorted_entries

_TRANSLATION_GLOSSARY_SURFACE_ID = "normalizer.translation_glossary"
_READ_TRANSLATION_GLOSSARY_LOCALE_ACTION = "read_translation_glossary_locale"
def read_translation_glossary(arguments: dict[str, Any]) -> dict[str, Any]:
    locale = _required_locale_argument(arguments, "locale")
    artifact_path, invoke_normalizer = _glossary_invoker(arguments, write=False)
    current = _read_locale_glossary(invoke_normalizer, locale)
    return response(
        operation="read",
        locale=locale,
        entries=list(current["entries"]),
        available_locales=list(current["available_locales"]),
        artifact_path=artifact_path,
        entry_status="unchanged",
    )


def upsert_translation_glossary_entry(arguments: dict[str, Any]) -> dict[str, Any]:
    locale = _required_locale_argument(arguments, "locale")
    artifact_path, invoke_normalizer = _glossary_invoker(arguments, write=True)
    english_term = _required_text(arguments, "english_term")
    canonical = _required_text(arguments, "canonical")
    aliases = dedupe_strings(_optional_string_list(arguments, "aliases"))
    current = _read_locale_glossary(invoke_normalizer, locale)
    entries = list(current["entries"])
    available_locales = list(current["available_locales"])

    replacement = {
        "english_term": english_term,
        "canonical": canonical,
        "aliases": aliases,
    }
    updated = []
    replaced = False
    for item in entries:
        if item["english_term"] == english_term:
            updated.append(replacement)
            replaced = True
            continue
        updated.append(item)
    if not replaced:
        updated.append(replacement)
    written = _write_entries(invoke_normalizer, locale, updated)
    return response(
        operation="upsert",
        locale=locale,
        entries=response_entries(written, fallback=updated),
        available_locales=available_locales,
        artifact_path=artifact_path,
        english_term=english_term,
        entry_status="updated" if replaced else "created",
    )


def remove_translation_glossary_entry(arguments: dict[str, Any]) -> dict[str, Any]:
    locale = _required_locale_argument(arguments, "locale")
    artifact_path, invoke_normalizer = _glossary_invoker(arguments, write=True)
    english_term = _required_text(arguments, "english_term")
    current = _read_locale_glossary(invoke_normalizer, locale)
    entries = list(current["entries"])
    available_locales = list(current["available_locales"])

    remaining = [item for item in entries if item["english_term"] != english_term]
    if len(remaining) == len(entries):
        return response(
            operation="remove",
            locale=locale,
            entries=entries,
            available_locales=available_locales,
            artifact_path=artifact_path,
            english_term=english_term,
            entry_status="not_found",
        )
    written = _write_entries(invoke_normalizer, locale, remaining)
    return response(
        operation="remove",
        locale=locale,
        entries=response_entries(written, fallback=remaining),
        available_locales=available_locales,
        artifact_path=artifact_path,
        english_term=english_term,
        entry_status="removed",
    )


def _glossary_invoker(
    arguments: dict[str, Any],
    *,
    write: bool,
) -> tuple[Path | None, Callable[[dict[str, Any]], dict[str, Any]]]:
    artifact_folder = _optional_text(arguments, "artifact_folder")
    artifact_path = Path(artifact_folder).expanduser().resolve() if artifact_folder else None
    invoker = _normalizer_edit_invoker if write else _normalizer_read_invoker
    return artifact_path, invoker(artifact_folder)


def _read_locale_glossary(
    invoke_normalizer: Callable[[dict[str, Any]], dict[str, Any]],
    locale: str,
) -> dict[str, Any]:
    result = invoke_normalizer({"action": _READ_TRANSLATION_GLOSSARY_LOCALE_ACTION, "locale": locale})
    value = result.get("value")
    if not isinstance(value, dict):
        raise ToolFailure("Glossary-Leseaktion lieferte kein gueltiges Value-Payload.")
    raw_entries = value.get("entries")
    if not isinstance(raw_entries, list):
        raise ToolFailure("Glossary-Leseaktion lieferte keine gueltige entries-Liste.")
    available_locales = result.get("allowed_values")
    if not isinstance(available_locales, list):
        available_locales = []
    return {
        "entries": response_entries({"value": value}, fallback=[]),
        "available_locales": [str(item) for item in available_locales if str(item).strip()],
    }


def _write_entries(
    invoke_normalizer: Callable[[dict[str, Any]], dict[str, Any]],
    locale: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {"active_locale": locale, "entries": sorted_entries(entries)}
    invoke_normalizer(
        {
            "action": "validate_surface",
            "surface_id": _TRANSLATION_GLOSSARY_SURFACE_ID,
            "value": payload,
        }
    )
    return invoke_normalizer(
        {
            "action": "write_surface",
            "surface_id": _TRANSLATION_GLOSSARY_SURFACE_ID,
            "value": payload,
        }
    )

__all__ = [name for name in globals() if not name.startswith("__")]
