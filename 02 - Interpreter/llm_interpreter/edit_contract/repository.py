"""Owner-local read-only helpers for edit-contract surfaces."""
from __future__ import annotations

import json
from pathlib import Path


def read_debug_capabilities(module_root: Path) -> dict:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    return {
        "module_key": str(manifest.get("module_key") or ""),
        "display_name": str(manifest.get("display_name") or ""),
        "capabilities": dict(manifest.get("debug_surface") or {}),
        "operation_links": _operation_links(manifest),
    }


def _operation_links(manifest: dict) -> list[dict[str, str]]:
    return [
        {
            "action": action,
            "label": action.replace("_", " ").title(),
            "contract_module": str(manifest.get("contract_module") or ""),
        }
        for action in manifest.get("actions", [])
        if isinstance(action, str) and action.strip()
    ]


__all__ = ["read_debug_capabilities"]
