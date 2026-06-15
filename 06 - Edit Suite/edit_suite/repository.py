"""Suite-local persistence limited to state/."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from . import policy, validation


def ensure_state_layout(state_root: Path) -> Path:
    state_root.mkdir(parents=True, exist_ok=True)
    return state_root


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        Path(temp_name).replace(path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return validation.require_json_object(payload, label=path.name)
    except (OSError, ValueError):
        return None


def ui_state_path(state_root: Path) -> Path:
    return state_root / policy.UI_STATE_NAME


def registry_cache_path(state_root: Path) -> Path:
    return state_root / policy.DISCOVERY_CACHE_NAME


def bundle_cache_path(state_root: Path, module_id: str) -> Path:
    return state_root / policy.BUNDLE_CACHE_DIR_NAME / f"{safe_module_id(module_id)}.json"


def load_ui_state(state_root: Path) -> dict:
    payload = load_json(ui_state_path(state_root)) or {}
    operation_contexts = payload.get("operation_contexts")
    return {
        "selected_module": str(payload.get("selected_module") or ""),
        "selected_section": str(payload.get("selected_section") or "Summary"),
        "window_geometry": str(payload.get("window_geometry") or ""),
        "operation_contexts": operation_contexts if isinstance(operation_contexts, dict) else {},
    }


def save_ui_state(state_root: Path, payload: dict) -> None:
    path = validation.ensure_state_child(state_root, ui_state_path(state_root))
    atomic_json_write(path, validation.require_json_object(payload, label="ui_state"))


def load_registry_cache(state_root: Path) -> dict | None:
    return load_json(registry_cache_path(state_root))


def save_registry_cache(state_root: Path, payload: dict) -> None:
    path = validation.ensure_state_child(state_root, registry_cache_path(state_root))
    atomic_json_write(path, validation.require_json_object(payload, label="registry_cache"))


def load_bundle_cache(state_root: Path, module_id: str) -> dict | None:
    return load_json(bundle_cache_path(state_root, module_id))


def save_bundle_cache(state_root: Path, module_id: str, payload: dict) -> None:
    path = validation.ensure_state_child(state_root, bundle_cache_path(state_root, module_id))
    atomic_json_write(path, validation.require_json_object(payload, label="bundle_cache"))


def safe_module_id(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in str(value or ""))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return validation.safe_filename(cleaned.strip("_"), fallback="unknown_module")
