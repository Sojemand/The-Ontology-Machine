"""Boundary I/O helpers for the validator subprocess contract."""
from __future__ import annotations

from pathlib import Path

from ..models.report_io import atomic_json_write
from ..models.structured_io import read_json_object


def load_request(path: Path) -> dict:
    return read_json_object(Path(path), label="Request")


def write_response(path: Path, payload: dict, *, atomic_write=atomic_json_write) -> None:
    atomic_write(Path(path), payload)
