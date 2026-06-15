from __future__ import annotations

import json
import subprocess
from typing import Any, Mapping

from .contract_client import _runtime_env
from . import semantic_control_kernel_bridge_config as _bridge_config
from .semantic_control_kernel_bridge_config import (
    BRIDGE_CONFIG_PATH,
    BRIDGE_CONFIG_SCHEMA_VERSION,
    DEFAULT_CALL_TIMEOUT_SECONDS,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    SemanticControlKernelBridgeConfig,
)
from .semantic_control_kernel_client_errors import SemanticControlKernelClientError


UNAVAILABLE_SAFE_MESSAGE = "The Semantic Control Kernel bridge is unavailable."


class SemanticControlKernelClient:
    def __init__(self) -> None:
        self._config: SemanticControlKernelBridgeConfig | None = None

    def list_mcp_tool_definitions(self, scope: str) -> dict[str, Any]:
        return self._invoke_json_command("list-mcp-tools", extra_args=("--scope", scope))

    def list_client_frontend_events(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self._invoke_json_command("list-client-events", stdin_payload=request)

    def submit_user_interaction_response(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self._invoke_json_command("submit-interaction-response", stdin_payload=request)

    def cancel_user_interaction(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self._invoke_json_command("cancel-interaction", stdin_payload=request)

    def list_event_scoped_tool_definitions(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self._invoke_json_command("list-event-scoped-tools", stdin_payload=request)

    def kernel_healthcheck(self) -> dict[str, Any]:
        return self._invoke_json_command("healthcheck")

    def call_tool(
        self,
        *,
        tool_name: str,
        visibility: str,
        model_arguments: Mapping[str, Any] | None = None,
        client_context: Mapping[str, Any] | None = None,
        event_scope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        envelope = {
            "schema_version": "semantic_control_kernel.mcp_request.v1",
            "transport": "mcp_server",
            "tool_name": tool_name,
            "visibility": visibility,
            "model_arguments": dict(model_arguments or {}),
            "client_context": dict(client_context or {"host_surface_identity": "mcp_server", "client_request_id": "mcp_server"}),
            "event_scope": dict(event_scope) if event_scope is not None else None,
        }
        try:
            return self._invoke_json_command("mcp-call", stdin_payload=envelope)
        except Exception:
            return _unavailable_tool_response(tool_name)

    def resolved_kernel_status(self) -> dict[str, Any]:
        config = self._bridge_config()
        return {
            "bridge_config_path": str(BRIDGE_CONFIG_PATH),
            "contract_module": config.contract_module,
            "module_root": str(config.module_root),
            "python_executable": str(config.python_executable),
            "call_timeout_seconds": config.call_timeout_seconds,
            "startup_timeout_seconds": config.startup_timeout_seconds,
        }

    def _invoke_json_command(
        self,
        command: str,
        *,
        stdin_payload: Mapping[str, Any] | None = None,
        extra_args: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        config = self._bridge_config()
        completed = subprocess.run(
            [str(config.python_executable), "-m", config.contract_module, command, *extra_args],
            cwd=config.module_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.call_timeout_seconds,
            env=_runtime_env(config.python_executable.parent.parent if config.python_executable.parent.name.lower() == "scripts" else config.python_executable.parent),
            input=json.dumps(dict(stdin_payload or {}), ensure_ascii=True) if stdin_payload is not None else None,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"Exitcode {completed.returncode}"
            raise SemanticControlKernelClientError(f"Semantic Control Kernel contract failed: {detail}")
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise SemanticControlKernelClientError("Semantic Control Kernel contract returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise SemanticControlKernelClientError("Semantic Control Kernel contract returned a non-object payload.")
        return payload

    def _bridge_config(self) -> SemanticControlKernelBridgeConfig:
        if self._config is None:
            self._config = _load_bridge_config()
        return self._config


def _load_bridge_config() -> SemanticControlKernelBridgeConfig:
    _bridge_config.BRIDGE_CONFIG_PATH = BRIDGE_CONFIG_PATH
    return _bridge_config.load_bridge_config()


def _unavailable_tool_response(tool_name: str) -> dict[str, Any]:
    return {
        "schema_version": "semantic_control_kernel.mcp_response.v1",
        "status": "failed",
        "tool_name": tool_name,
        "effect": "none",
        "user_visible_summary": UNAVAILABLE_SAFE_MESSAGE,
        "mirror_event": None,
        "error": {
            "code": "semantic_control_kernel_unavailable",
            "category": "technical_failure",
            "safe_message": UNAVAILABLE_SAFE_MESSAGE,
        },
    }


__all__ = [
    "BRIDGE_CONFIG_PATH",
    "BRIDGE_CONFIG_SCHEMA_VERSION",
    "DEFAULT_CALL_TIMEOUT_SECONDS",
    "DEFAULT_STARTUP_TIMEOUT_SECONDS",
    "MAX_TIMEOUT_SECONDS",
    "SemanticControlKernelBridgeConfig",
    "SemanticControlKernelClient",
    "SemanticControlKernelClientError",
    "_load_bridge_config",
]
