"""I/O helpers for bootstrap and runtime reports."""

from __future__ import annotations

import json
from pathlib import Path


def load_json_object(path: Path, *, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return payload
