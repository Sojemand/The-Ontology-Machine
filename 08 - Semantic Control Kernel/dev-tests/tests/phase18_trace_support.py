from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def fixture(schema_version: str) -> dict:
    return json.loads((FIXTURES / f"{schema_version.replace('.', '__')}.valid.json").read_text(encoding="utf-8"))
