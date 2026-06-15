from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..models.serialization import atomic_text_write


def write_component(path: str | Path, payload: Mapping[str, Any]) -> str:
    target = Path(path)
    atomic_text_write(target, json.dumps(dict(payload), indent=2, sort_keys=True) + "\n")
    return str(target)


def artifact_ref(path: str | Path, *, root: str | Path | None = None) -> dict[str, str]:
    target = Path(path)
    if root is None:
        return {"artifact_path": str(target)}
    try:
        return {"artifact_path": target.relative_to(Path(root)).as_posix()}
    except ValueError:
        return {"artifact_path": str(target)}
