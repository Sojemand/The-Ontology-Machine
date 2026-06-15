"""Hard contract validation for sibling-module subprocess calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import ModuleContractError


def ensure_contract_runtime_ready(*, display_name: str, python_executable: Path, manifest_path: Path) -> None:
    if not python_executable.exists():
        raise FileNotFoundError(f"Bundled runtime is missing for {display_name}: {python_executable}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"module-manifest.json is missing for {display_name}: {manifest_path}")


def load_contract_response(response_path: Path) -> dict[str, Any]:
    if not response_path.exists():
        return {}
    try:
        payload = json.loads(response_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ModuleContractError(f"Response file is invalid: {response_path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise ModuleContractError(f"Response file is not a JSON object: {response_path}")
    return payload
