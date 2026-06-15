"""File-backed repository helpers for runtime-policy bundles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_runtime_semantic_assets(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileNotFoundError(f"Runtime-Policy-Bundle konnte nicht gelesen werden: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Runtime-Policy-Bundle enthaelt ungueltiges JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Runtime-Policy-Bundle muss ein JSON-Objekt sein.")
    return payload
