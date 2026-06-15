"""Subprocess client for owner-local Vision Pipeline contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .atomic_io import atomic_json_write

MODULE_DIRS = {
    "orchestrator": "00 - Orchestrator",
    "optimizer": "01 - Optimizer",
    "interpreter": "02 - Interpreter",
    "validator": "03 - Validator",
    "normalizer": "04 - Normalizer",
    "corpus_builder": "05 - Corpus Builder",
}

DEFAULT_TIMEOUT_SECONDS = 120
CONTRACT_CALLS_DIR_ENV = "VISION_MCP_CONTRACT_CALLS_DIR"


class ContractError(RuntimeError):
    """Raised when an owner contract cannot be invoked."""


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    root: Path
    display_name: str
    contract_module: str
    runtime_dir: Path
    python_executable: Path
    actions: tuple[str, ...]
    manifest_actions: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ContractEndpoint:
    module_key: str
    contract_module: str
    allowed_actions: tuple[str, ...]
    check_manifest_actions: bool = False
    manifest_actions_key: str = "actions"

def pipeline_root() -> Path:
    return Path(__file__).resolve().parents[2]


def module_spec(module_key: str) -> ModuleSpec:
    try:
        module_dir = MODULE_DIRS[module_key]
    except KeyError as exc:
        raise ContractError(f"Unbekanntes Modul: {module_key}") from exc
    root = pipeline_root() / module_dir
    manifest_path = root / "module-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ContractError(f"Manifest nicht lesbar: {manifest_path}") from exc
    runtime_dir = root / str(manifest.get("runtime_dir") or "runtime/python")
    actions = tuple(str(action) for action in manifest.get("actions", []) if str(action).strip())
    admin_actions = tuple(str(action) for action in manifest.get("admin_actions", []) if str(action).strip())
    return ModuleSpec(
        key=str(manifest.get("module_key") or module_key),
        root=root,
        display_name=str(manifest.get("display_name") or module_key),
        contract_module=str(manifest.get("contract_module") or ""),
        runtime_dir=runtime_dir,
        python_executable=_runtime_python(runtime_dir),
        actions=actions,
        manifest_actions={"actions": actions, "admin_actions": admin_actions},
    )


def invoke_product_contract(module_key: str, payload: dict[str, Any], *, allowed_actions: tuple[str, ...], timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    spec = module_spec(module_key)
    endpoint = ContractEndpoint(module_key=module_key, contract_module=spec.contract_module, allowed_actions=allowed_actions, check_manifest_actions=True)
    return invoke_endpoint(endpoint, payload, timeout=timeout)


def invoke_contract(module_key: str, payload: dict[str, Any], *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    spec = module_spec(module_key)
    endpoint = ContractEndpoint(
        module_key=module_key,
        contract_module=spec.contract_module,
        allowed_actions=spec.actions,
        check_manifest_actions=True,
    )
    return invoke_endpoint(endpoint, payload, timeout=timeout)


def invoke_endpoint(endpoint: ContractEndpoint, payload: dict[str, Any], *, timeout: int = DEFAULT_TIMEOUT_SECONDS, env_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    spec = module_spec(endpoint.module_key)
    action = str(payload.get("action") or "").strip()
    if action and action not in endpoint.allowed_actions:
        raise ContractError(f"{spec.display_name} bietet die MCP-freigegebene Action nicht an: {action}")
    manifest_actions = spec.manifest_actions.get(endpoint.manifest_actions_key, ())
    if endpoint.check_manifest_actions and action and action not in manifest_actions:
        raise ContractError(f"{spec.display_name} bietet die Action nicht an: {action}")
    contract_module = str(endpoint.contract_module or "").strip()
    if not contract_module:
        raise ContractError(f"{spec.display_name} hat kein contract_module.")
    if not spec.python_executable.exists():
        raise ContractError(f"Runtime fehlt fuer {spec.display_name}: {spec.python_executable}")
    temp_dir = _create_contract_call_dir(endpoint.module_key)
    try:
        request_path = temp_dir / "request.json"
        response_path = temp_dir / "response.json"
        atomic_json_write(request_path, payload)
        runtime_env = _runtime_env(spec.runtime_dir)
        if env_overrides:
            runtime_env.update({str(key): str(value) for key, value in env_overrides.items() if value is not None})
        command = [str(spec.python_executable), "-m", contract_module, "--request", str(request_path), "--response", str(response_path)]
        completed = subprocess.run(
            command,
            cwd=spec.root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=runtime_env,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"Exitcode {completed.returncode}"
            raise ContractError(f"{spec.display_name} Contract fehlgeschlagen: {detail}")
        response = _load_response(response_path)
        return response
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def contract_calls_root() -> Path:
    override = str(os.environ.get(CONTRACT_CALLS_DIR_ENV) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "state" / "contract_calls"


def _create_contract_call_dir(module_key: str) -> Path:
    root = contract_calls_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ContractError(f"Contract-Call-State ist nicht beschreibbar: {root}") from exc
    for _index in range(20):
        candidate = root / f"{module_key}-{uuid4().hex}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
        except OSError as exc:
            raise ContractError(f"Contract-Call-Temp-Verzeichnis ist nicht beschreibbar: {root}") from exc
    raise ContractError(f"Contract-Call-Temp-Verzeichnis konnte nicht eindeutig angelegt werden: {root}")


def _runtime_python(runtime_dir: Path) -> Path:
    for relative in ("python.exe", "Scripts/python.exe", "bin/python"):
        candidate = runtime_dir / relative
        if candidate.exists():
            return candidate
    return runtime_dir / "python.exe"


def _runtime_env(runtime_dir: Path) -> dict[str, str]:
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHOME": str(runtime_dir),
        "PYTHONPATH": "",
        "PYTHONNOUSERSITE": "1",
    }
    tcl_dir = runtime_dir / "tcl"
    if (tcl_dir / "tcl8.6").exists():
        env["TCL_LIBRARY"] = str(tcl_dir / "tcl8.6")
    if (tcl_dir / "tk8.6").exists():
        env["TK_LIBRARY"] = str(tcl_dir / "tk8.6")
    return env


def _load_response(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContractError(f"Contract-Response fehlt: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ContractError(f"Contract-Response ist kein gueltiges JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"Contract-Response muss ein JSON-Objekt sein: {path}")
    return payload
