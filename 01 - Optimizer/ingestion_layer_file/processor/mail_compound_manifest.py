"""Manifest loading for temporary mail bundles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def require_manifest_path(metadata: dict[str, object]) -> Path:
    path_text = str((metadata or {}).get("mail_bundle_path", "")).strip()
    if not path_text:
        raise RuntimeError("Mail-Plugin lieferte keinen mail_bundle_path.")
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Mail-Bundle fehlt: {path}")
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Mail-Bundle ist ungueltig: {path}")
    return payload
