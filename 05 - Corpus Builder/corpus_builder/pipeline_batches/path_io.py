from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from ..models.serialization import atomic_bytes_write, atomic_json_write


def read_json(path: str | Path) -> dict[str, Any]:
    with open(as_os_path(Path(path)), "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> str:
    target = Path(path)
    ensure_directory(target.parent)
    atomic_json_write(target, dict(payload), sort_keys=True, trailing_newline=True)
    return str(target)


def write_bytes(path: str | Path, payload: bytes) -> str:
    target = Path(path)
    ensure_directory(target.parent)
    atomic_bytes_write(target, payload)
    return str(target)


def ensure_directory(path: str | Path) -> str:
    target = Path(path)
    os.makedirs(as_os_path(target), exist_ok=True)
    return str(target)


def as_os_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    text = str(resolved)
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text
