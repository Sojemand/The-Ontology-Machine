from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..state import atomic_json_write


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    atomic_json_write(path, dict(payload), sort_keys=True, trailing_newline=True)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Manifest must be a JSON object.")
    return payload
