from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import atomic_write_json


def write_json_file(path: str | Path, payload: Mapping[str, Any]) -> None:
    atomic_write_json(path, dict(payload))
