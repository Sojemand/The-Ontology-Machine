"""I/O helpers for request enrichment payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..state import atomic_json_write


def raw_stem(raw_path: Path) -> str:
    name = raw_path.name
    if name.endswith(".raw.json"):
        return name[: -len(".raw.json")]
    if name.endswith(".json"):
        return name[: -len(".json")]
    return raw_path.stem


def write_request_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_json_write(path, payload, trailing_newline=True)


def load_json_object(path: Path, *, error_prefix: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{error_prefix} must be a JSON object: {path}")
    return payload
