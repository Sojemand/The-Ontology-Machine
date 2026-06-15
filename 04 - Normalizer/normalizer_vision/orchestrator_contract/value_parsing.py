"""Shared value parsers for Normalizer contract payloads."""
from __future__ import annotations

from pathlib import Path


def required_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def required_path(payload: dict, key: str) -> Path:
    value = required_string(payload, key)
    if value is None:
        raise ValueError(f"{key} fehlt oder ist ungueltig.")
    return Path(value)


def optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Pfadoptionen muessen Strings sein.")
    stripped = value.strip()
    return Path(stripped) if stripped else None


def optional_worker_count(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("worker_count muss eine positive Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("worker_count muss eine positive Ganzzahl sein.") from None
    if parsed < 1:
        raise ValueError("worker_count muss eine positive Ganzzahl sein.")
    return parsed


def optional_non_empty_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Optionale Textfelder muessen Strings sein.")
    stripped = value.strip()
    return stripped or None


def projection_ids(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("projection_ids muss eine Liste von Strings sein.")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"projection_ids[{index}] muss ein String sein.")
        projection_id = item.strip()
        if not projection_id:
            raise ValueError(f"projection_ids[{index}] darf nicht leer sein.")
        if projection_id in seen:
            continue
        seen.add(projection_id)
        result.append(projection_id)
    return tuple(result)
