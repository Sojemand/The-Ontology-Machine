from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import ensure_text


def iter_collection(collection: Any) -> list[Any]:
    if collection is None:
        return []
    try:
        count = int(collection.Count or 0)
    except Exception:
        return []
    values: list[Any] = []
    for index in range(1, count + 1):
        try:
            values.append(collection.Item(index))
        except Exception:
            continue
    return values


def safe_get(target: Any, name: str) -> Any:
    try:
        return getattr(target, name)
    except Exception:
        return None


def normalize_store_path(value: Any) -> str:
    candidate = ensure_text(value).strip()
    if not candidate:
        return ""
    return str(Path(candidate).resolve()).lower()


def normalize_datetime(value: Any) -> str:
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except Exception:
            pass
    return ensure_text(value).strip().replace("/", "-")
