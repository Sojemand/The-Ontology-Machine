"""Boundary I/O helpers for the normalizer subprocess contract."""
from __future__ import annotations

from pathlib import Path

from ..models.serialization import atomic_json_write, read_json_object


def load_request(path: Path) -> dict:
    return read_json_object(Path(path), label="Request")


def write_response(path: Path, payload: dict) -> None:
    atomic_json_write(Path(path), payload)
