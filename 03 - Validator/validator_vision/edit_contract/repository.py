"""Owner-local read/write helpers for validator edit surfaces."""
from __future__ import annotations

import json
from pathlib import Path

from ..models.report_io import atomic_json_write
from ..paths import default_config_path
from . import validation


def read_settings(home_root: Path) -> dict:
    return validation.settings_slice(_read_full_payload(home_root))


def write_settings(home_root: Path, payload: dict) -> dict:
    full_payload = validation.merge_settings_payload(_read_full_payload(home_root), payload)
    _write_full_payload(home_root, full_payload)
    return validation.settings_slice(full_payload)


def read_report_preview_policy(home_root: Path) -> dict:
    return validation.policy_slice(_read_full_payload(home_root))


def write_report_preview_policy(home_root: Path, payload: dict) -> dict:
    full_payload = validation.merge_policy_payload(_read_full_payload(home_root), payload)
    _write_full_payload(home_root, full_payload)
    return validation.policy_slice(full_payload)


def read_debug_capabilities(module_root: Path) -> dict:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    return {
        "module_key": str(manifest.get("module_key") or ""),
        "display_name": str(manifest.get("display_name") or ""),
        "capabilities": dict(manifest.get("debug_surface") or {}),
        "operation_links": [
            {
                "action": action,
                "label": action.replace("_", " ").title(),
                "contract_module": str(manifest.get("contract_module") or ""),
            }
            for action in manifest.get("actions", [])
            if isinstance(action, str) and action.strip()
        ],
    }


def _read_full_payload(home_root: Path) -> dict:
    return validation.read_full_payload(default_config_path(home_root))


def _write_full_payload(home_root: Path, payload: dict) -> None:
    atomic_json_write(default_config_path(home_root), payload)
