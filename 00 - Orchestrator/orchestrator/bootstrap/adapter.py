"""Bootstrap boundary helpers for registry, manifest and runtime I/O."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from .exceptions import ModuleRegistryError

ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ORCHESTRATOR_ROOT / "state"
MODULE_REGISTRY_PATH = ORCHESTRATOR_ROOT / "module-registry.json"


def load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ModuleRegistryError(f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ModuleRegistryError(f"{label} is invalid: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise ModuleRegistryError(f"{label} must be a JSON object: {path}")
    return payload


def resolve_registry_path(registry_path: Path | None = None) -> Path:
    return Path(registry_path or MODULE_REGISTRY_PATH).resolve()


def manifest_path(module_root: Path) -> Path:
    return module_root / "module-manifest.json"


def resolve_module_root(registry_path: Path, raw_entry: str | dict[str, Any]) -> Path:
    if isinstance(raw_entry, str):
        raw_path = raw_entry
    elif isinstance(raw_entry, dict):
        raw_path = str(raw_entry.get("path", "")).strip()
    else:
        raise ModuleRegistryError(f"Invalid module entry in {registry_path}: {raw_entry!r}")
    if not raw_path:
        raise ModuleRegistryError(f"Module entry without path in {registry_path}")
    candidate = Path(raw_path)
    return ((registry_path.parent / candidate) if not candidate.is_absolute() else candidate).resolve()


def bundled_python_candidates(module_root: Path, runtime_dir: Path | None = None) -> tuple[Path, ...]:
    runtime_root = runtime_dir or (module_root / "runtime" / "python")
    exe_name = f"python{'.exe' if sys.platform == 'win32' else ''}"
    return (
        runtime_root / exe_name,
        runtime_root / "Scripts" / exe_name,
        runtime_root / "bin" / "python",
    )


def require_python_module(module_name: str) -> None:
    importlib.import_module(module_name)
