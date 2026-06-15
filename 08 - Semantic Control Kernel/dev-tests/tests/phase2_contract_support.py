from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"

def _fixture(schema_version: str) -> dict[str, Any]:
    path = FIXTURE_ROOT / (schema_version.replace(".", "__") + ".valid.json")
    return json.loads(path.read_text(encoding="utf-8"))

def _fixture_prefix(schema_version: str) -> str:
    return schema_version.replace(".", "__")

def _set_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
    parts = field_path.split(".")
    current: Any = payload
    for part in parts[:-1]:
        if part.endswith("[]"):
            key = part[:-2]
            current = current[key][0]
        else:
            current = current[part]
    last = parts[-1]
    if last.endswith("[]"):
        key = last[:-2]
        current[key] = [value]
    else:
        current[last] = value
