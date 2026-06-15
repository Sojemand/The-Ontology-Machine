"""Adapter helpers for request/response and raw-path I/O."""
from __future__ import annotations

import json
from pathlib import Path


def load_request(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Request muss ein JSON-Objekt sein.")
    return payload


def write_response(path: Path, payload: dict, *, atomic_write) -> None:
    atomic_write(path, payload)
