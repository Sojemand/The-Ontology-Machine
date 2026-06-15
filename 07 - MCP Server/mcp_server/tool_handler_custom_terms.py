from __future__ import annotations

import unicodedata

from .tool_handler_deps import *


def normalize_term_specs(value: Any, *, label: str, default_description: str) -> list[dict[str, Any]]:
    items = _coerce_items(value, label=label)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        term = _normalize_one_term(item, label=label, default_description=default_description)
        code = str(term["code"])
        if code in seen:
            continue
        seen.add(code)
        normalized.append(term)
    if not normalized:
        raise ToolFailure(f"{label} darf nicht leer sein.")
    return normalized


def normalize_optional_term_specs(value: Any, *, label: str, default_description: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    return normalize_term_specs(value, label=label, default_description=default_description)


def normalize_marker_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        items = _split_text_list(value)
    elif isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, str):
                raise ToolFailure("text_markers muss eine String-Liste oder ein Textblock sein.")
            items.extend(_split_text_list(item))
    else:
        raise ToolFailure("text_markers muss eine String-Liste oder ein Textblock sein.")
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        marker = item.strip()
        if marker and marker.casefold() not in seen:
            seen.add(marker.casefold())
            result.append(marker)
    return result


def stable_code(value: str) -> str:
    text = _ascii_fold(value).casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "custom_term"


def _coerce_items(value: Any, *, label: str) -> list[Any]:
    if isinstance(value, str):
        return _split_text_list(value)
    if isinstance(value, list):
        items: list[Any] = []
        for item in value:
            if isinstance(item, str):
                items.extend(_split_text_list(item))
            elif isinstance(item, dict):
                items.append(item)
            else:
                raise ToolFailure(f"{label} muss Text, eine Text-Liste oder eine Objekt-Liste sein.")
        return items
    raise ToolFailure(f"{label} muss Text, eine Text-Liste oder eine Objekt-Liste sein.")


def _normalize_one_term(item: Any, *, label: str, default_description: str) -> dict[str, Any]:
    if isinstance(item, str):
        item_label = item.strip()
        if not item_label:
            raise ToolFailure(f"{label} enthaelt einen leeren Eintrag.")
        return {"code": stable_code(item_label), "label": item_label, "description": default_description}
    if not isinstance(item, dict):
        raise ToolFailure(f"{label} enthaelt einen ungueltigen Eintrag.")
    item_label = str(item.get("label") or item.get("name") or item.get("code") or "").strip()
    if not item_label:
        raise ToolFailure(f"{label} Eintrag braucht label, name oder code.")
    result = {
        "code": stable_code(str(item.get("code") or item_label)),
        "label": item_label,
        "description": str(item.get("description") or default_description).strip(),
    }
    for key in ("aliases", "value_type"):
        if key in item and item[key] not in (None, ""):
            result[key] = item[key]
    return result


def _split_text_list(value: str) -> list[str]:
    return [item.strip(" -\t") for item in re.split(r"[\n,;]+", value) if item.strip(" -\t")]


def _ascii_fold(value: str) -> str:
    replacements = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})
    value = value.translate(replacements)
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")


__all__ = [name for name in globals() if not name.startswith("__")]
