"""Boundary I/O helpers for the Corpus Builder subprocess contract."""
from __future__ import annotations

import json
from pathlib import Path

from ..models.serialization import atomic_json_write


def load_request(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Request muss ein JSON-Objekt sein.")
    return payload


def write_response(path: Path, payload: dict) -> None:
    atomic_json_write(Path(path), payload)
