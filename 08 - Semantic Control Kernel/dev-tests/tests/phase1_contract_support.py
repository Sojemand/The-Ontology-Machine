from __future__ import annotations

import json
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload
