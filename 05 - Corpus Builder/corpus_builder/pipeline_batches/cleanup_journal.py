from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .path_io import write_json


def write_cleanup_journal(path: str | Path, payload: Mapping[str, Any]) -> str:
    return write_json(path, payload)
