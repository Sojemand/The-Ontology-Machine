"""Boundary stage for taxonomy JSON file I/O."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.serialization import load_json


def read_taxonomy_json(path: Path) -> dict[str, Any]:
    return load_json(path)
