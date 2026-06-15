"""Value parsing helpers for minimal custom releases."""
from __future__ import annotations

import re
from typing import Any

from ..taxonomy.types import normalize_lookup_token
from ..taxonomy_sources import policy as source_policy

_LIST_SPLIT_RE = re.compile(r"[\n,;]+")


def single_term(value: Any, *, default_code: str, default_label: str, default_description: str) -> dict[str, Any]:
    if value is None:
        return term({"code": default_code, "label": default_label, "description": default_description}, label="term")
    return term(value, label="term")


def term_list(value: Any, *, label: str, require_items: bool) -> list[dict[str, Any]]:
    if value is None:
        if require_items:
            raise ValueError(f"{label} darf nicht leer sein.")
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    result = [term(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
    if require_items and not result:
        raise ValueError(f"{label} darf nicht leer sein.")
    return dedupe_terms(result)


def term(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, str):
        raw_label = required_text(value, label=label)
        code = normalize_lookup_token(raw_label)
        return {"code": code, "label": raw_label, "description": raw_label, "aliases": [], "value_type": "string"}
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt oder String sein.")
    raw_label = required_text(value.get("label") or value.get("code"), label=f"{label}.label")
    code = normalize_lookup_token(required_text(value.get("code") or raw_label, label=f"{label}.code"))
    result = {
        "code": code,
        "label": raw_label,
        "description": required_text(value.get("description") or raw_label, label=f"{label}.description"),
        "aliases": string_list(value.get("aliases"), label=f"{label}.aliases", required=False),
        "value_type": value_type(value.get("value_type")),
    }
    for key in ("promotion_slot", "promotion_cardinality", "query_role", "display_rank"):
        if key in value and value[key] not in (None, ""):
            result[key] = value[key]
    if isinstance(value.get("semantic_binding"), dict):
        result["semantic_binding"] = dict(value["semantic_binding"])
    return result


def text_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {"label": item["label"], "description": item["description"], "aliases": list(item.get("aliases") or [])}


def other_text(description: str) -> dict[str, Any]:
    return {"label": "Other", "description": description, "aliases": []}


def string_list(value: Any, *, label: str, required: bool) -> list[str]:
    if value is None or value == "":
        if required:
            raise ValueError(f"{label} darf nicht leer sein.")
        return []
    if isinstance(value, str):
        result = [item.strip() for item in _LIST_SPLIT_RE.split(value) if item and item.strip()]
    elif isinstance(value, list):
        result = [required_text(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
    else:
        raise ValueError(f"{label} muss eine Liste oder kommagetrennter Text sein.")
    result = dedupe(result)
    if required and not result:
        raise ValueError(f"{label} darf nicht leer sein.")
    return result


def derive_markers(*values: str) -> list[str]:
    markers: list[str] = []
    for value in values:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", str(value or "").casefold()):
            if word not in markers:
                markers.append(word)
            if len(markers) >= 10:
                return markers
    return markers


def value_type(value: Any) -> str:
    text = str(value or "string").strip()
    if text not in {"string", "date_or_string", "number_or_string", "number_or_money_string"}:
        raise ValueError(f"value_type ist ungueltig: {text}")
    return text


def stable_id(value: Any, *, label: str) -> str:
    text = required_text(value, label=label)
    if not re.fullmatch(r"[a-z0-9]+(?:[._][a-z0-9]+)*", text):
        raise ValueError(f"{label} muss eine stabile ASCII-ID sein.")
    return text


def required_text(value: Any, *, label: str) -> str:
    return source_policy.require_text(value, label=label)


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def dedupe_terms(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        if item["code"] in seen:
            continue
        seen.add(item["code"])
        result.append(item)
    return result


def generated_files(projection_id: str, locales: list[str]) -> list[str]:
    return [
        "release.yaml",
        "master.core.yaml",
        *[f"master.text.{locale}.yaml" for locale in locales],
        f"projections/{projection_id}.core.yaml",
        *[f"projections/{projection_id}.text.{locale}.yaml" for locale in locales],
    ]
