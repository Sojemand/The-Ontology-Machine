"""Adapter helpers for request/response JSON I/O."""
from __future__ import annotations

import json
from pathlib import Path

from . import validation


def load_request(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return validation.require_object_payload(payload)


def write_response(path: Path, payload: dict, *, atomic_write) -> None:
    atomic_write(path, payload)
