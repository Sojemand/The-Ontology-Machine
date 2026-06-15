from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .semantic_control_kernel_client_errors import SemanticControlKernelClientError


DEFAULT_CALL_TIMEOUT_SECONDS = 120
DEFAULT_STARTUP_TIMEOUT_SECONDS = 15
MAX_TIMEOUT_SECONDS = 3600
BRIDGE_CONFIG_SCHEMA_VERSION = "mcp.semantic_control_kernel_bridge.v1"
BRIDGE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "semantic_control_kernel_bridge.json"


@dataclass(frozen=True)
class SemanticControlKernelBridgeConfig:
    module_root: Path
    contract_module: str
    python_executable: Path
    call_timeout_seconds: int
    startup_timeout_seconds: int


def load_bridge_config() -> SemanticControlKernelBridgeConfig:
    payload = _read_bridge_config()
    kernel_config = payload.get("semantic_control_kernel") if isinstance(payload.get("semantic_control_kernel"), Mapping) else {}
    module_root = _resolve_module_root(kernel_config)
    manifest_path = module_root / "module-manifest.json"
    if not manifest_path.exists():
        raise SemanticControlKernelClientError(f"Semantic Control Kernel manifest missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SemanticControlKernelClientError(f"Semantic Control Kernel manifest is not valid JSON: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise SemanticControlKernelClientError(f"Semantic Control Kernel manifest is not an object: {manifest_path}")
    runtime_dir = module_root / str(manifest.get("runtime_dir") or "runtime/python")
    contract_module = str(kernel_config.get("contract_module") or manifest.get("contract_module") or "").strip()
    if not contract_module:
        raise SemanticControlKernelClientError("Semantic Control Kernel contract_module is missing.")
    contract_path = module_root / "semantic_control_kernel" / "orchestrator_contract.py"
    if not contract_path.exists():
        raise SemanticControlKernelClientError(f"Semantic Control Kernel contract entry point missing: {contract_path}")
    python_executable = _runtime_python(runtime_dir)
    if not python_executable.exists():
        raise SemanticControlKernelClientError(f"Semantic Control Kernel runtime missing: {python_executable}")
    return SemanticControlKernelBridgeConfig(
        module_root=module_root,
        contract_module=contract_module,
        python_executable=python_executable,
        call_timeout_seconds=_timeout_seconds(kernel_config.get("call_timeout_seconds"), "call_timeout_seconds", DEFAULT_CALL_TIMEOUT_SECONDS),
        startup_timeout_seconds=_timeout_seconds(kernel_config.get("startup_timeout_seconds"), "startup_timeout_seconds", DEFAULT_STARTUP_TIMEOUT_SECONDS),
    )


def _read_bridge_config() -> dict[str, Any]:
    if BRIDGE_CONFIG_PATH.exists():
        try:
            payload = json.loads(BRIDGE_CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise SemanticControlKernelClientError(f"Bridge config is not valid JSON: {BRIDGE_CONFIG_PATH}") from exc
        if not isinstance(payload, dict):
            raise SemanticControlKernelClientError(f"Bridge config is not an object: {BRIDGE_CONFIG_PATH}")
        if payload.get("schema_version") != BRIDGE_CONFIG_SCHEMA_VERSION:
            raise SemanticControlKernelClientError(f"Bridge config schema_version mismatch: {BRIDGE_CONFIG_PATH}")
        if payload.get("enabled") is False:
            raise SemanticControlKernelClientError("Semantic Control Kernel bridge is disabled by configuration.")
        return payload
    return {
        "schema_version": BRIDGE_CONFIG_SCHEMA_VERSION,
        "enabled": True,
        "semantic_control_kernel": {
            "module_root": "../08 - Semantic Control Kernel",
            "contract_module": "semantic_control_kernel.orchestrator_contract",
            "call_timeout_seconds": DEFAULT_CALL_TIMEOUT_SECONDS,
            "startup_timeout_seconds": DEFAULT_STARTUP_TIMEOUT_SECONDS,
        },
    }


def _resolve_module_root(kernel_config: Mapping[str, Any]) -> Path:
    explicit = str(kernel_config.get("module_root") or "").strip()
    if explicit:
        return _resolve_against_mcp_root(explicit)
    env_override = str(os.environ.get("SEMANTIC_CONTROL_KERNEL_MODULE_ROOT") or "").strip()
    if env_override:
        return Path(env_override).resolve(strict=False)
    return _resolve_against_mcp_root("../08 - Semantic Control Kernel")


def _resolve_against_mcp_root(value: str) -> Path:
    mcp_root = Path(__file__).resolve().parents[1]
    return (mcp_root / value).resolve(strict=False)


def _runtime_python(runtime_dir: Path) -> Path:
    for relative in ("python.exe", "Scripts/python.exe", "bin/python"):
        candidate = runtime_dir / relative
        if candidate.exists():
            return candidate
    return runtime_dir / "python.exe"


def _timeout_seconds(value: object, field: str, default: int) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        raise SemanticControlKernelClientError(f"Bridge config {field} must be an integer between 1 and {MAX_TIMEOUT_SECONDS}.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SemanticControlKernelClientError(f"Bridge config {field} must be an integer between 1 and {MAX_TIMEOUT_SECONDS}.") from exc
    if parsed < 1 or parsed > MAX_TIMEOUT_SECONDS:
        raise SemanticControlKernelClientError(f"Bridge config {field} must be between 1 and {MAX_TIMEOUT_SECONDS} seconds.")
    return parsed


__all__ = [
    "BRIDGE_CONFIG_PATH",
    "BRIDGE_CONFIG_SCHEMA_VERSION",
    "DEFAULT_CALL_TIMEOUT_SECONDS",
    "DEFAULT_STARTUP_TIMEOUT_SECONDS",
    "MAX_TIMEOUT_SECONDS",
    "SemanticControlKernelBridgeConfig",
    "load_bridge_config",
]
