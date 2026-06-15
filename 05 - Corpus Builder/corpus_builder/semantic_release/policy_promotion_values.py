from __future__ import annotations

import json
import re
from typing import Any


_PATH_SEGMENT_RE = re.compile(r"(?P<name>[^.\[\]]+)(?:\[(?P<index>\d+|\*)\])?")


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip().casefold())
    return text or None


def _compact_text(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    compact = re.sub(r"[^0-9a-z]+", "", normalized)
    return compact or None


def _promotion_values(value: Any, *, cardinality: str) -> list[Any]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", [], {})]
    return [value]


def _display_value(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (dict, list)):
        return json_dumps(value)
    return str(value)


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return None
    normalized = text.replace(".", "").replace(",", ".") if "," in text else text
    try:
        return float(normalized)
    except ValueError:
        return None


def _date_value(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _resolve_path_segments(payload: Any, path: str) -> Any:
    if not path:
        return None
    return _resolve_segments(payload, path.split("."))


def _resolve_segments(current: Any, segments: list[str]) -> Any:
    if not segments:
        return current
    segment = segments[0]
    match = _PATH_SEGMENT_RE.fullmatch(segment)
    if match is None or not isinstance(current, dict):
        return None
    name = match.group("name")
    if name not in current:
        return None
    child = current[name]
    index = match.group("index")
    if index is None:
        return _resolve_segments(child, segments[1:])
    if not isinstance(child, list):
        return None
    if index == "*":
        values = [_resolve_segments(item, segments[1:]) for item in child]
        return [item for item in values if item not in (None, "", [], {})]
    idx = int(index)
    if idx < 0 or idx >= len(child):
        return None
    return _resolve_segments(child[idx], segments[1:])
