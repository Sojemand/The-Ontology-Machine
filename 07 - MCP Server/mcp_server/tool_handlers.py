"""Path-stable facade for MCP tool handlers."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

from . import support_monitor
from .contract_client import ContractError, module_spec
from .permissions import PermissionDenied, PermissionPolicyError, assert_tool_allowed
from .tool_catalog import catalog_cache_token, tool_definitions
from .tool_handler_contracts import _invoke_admin, _invoke_edit, _invoke_product
from .tool_handler_pipeline_context import _orchestrator_ui_state_path
from .tool_handler_pipeline_store import _pipeline_runs_dir, _state_dir
from .tool_handler_registry import handlers as _registry_handlers
from .tool_handler_registry import sync_patchable_hooks
from .tool_handler_runtime_state import _PIPELINE_RUN_PROCESSES, subprocess
from .tool_handler_types import ToolFailure, ToolHandler
from .tool_schema_validation import validate_arguments
from .semantic_control_kernel_visibility import authorize_tool_call


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    call_arguments = arguments or {}
    guard = authorize_tool_call(name, call_arguments)
    if guard["response"] is not None:
        return guard["response"]
    try:
        handler = _handlers()[name]
    except KeyError as exc:
        raise ToolFailure(f"Unbekanntes Tool: {name}") from exc
    if guard["enforce_permissions"]:
        try:
            assert_tool_allowed(name)
        except (PermissionDenied, PermissionPolicyError) as exc:
            raise ToolFailure(str(exc)) from exc
    _validate_catalog_arguments(name, call_arguments)
    try:
        _sync_patchable_hooks()
        return handler(call_arguments)
    except support_monitor.SupportError as exc:
        raise ToolFailure(str(exc)) from exc
    except ContractError as exc:
        support_monitor.record_exception_event(module_key="mcp_server", action=name, message=str(exc), exc=exc)
        raise ToolFailure(str(exc)) from exc


def result_as_text(result: dict[str, Any]) -> str:
    return str(result.get("message") or result.get("status") or "OK")


def _sync_patchable_hooks() -> None:
    sync_patchable_hooks(globals())


def _validate_catalog_arguments(tool_name: str, arguments: dict[str, Any]) -> None:
    validate_arguments(tool_name, arguments, _catalog_input_schemas().get(tool_name))


def _catalog_input_schemas() -> dict[str, dict[str, Any]]:
    return _catalog_input_schema_snapshot(catalog_cache_token())


@lru_cache(maxsize=8)
def _catalog_input_schema_snapshot(cache_token: tuple[object, ...]) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for tool in tool_definitions():
        name = str(tool.get("name") or "").strip()
        schema = tool.get("inputSchema")
        if name and isinstance(schema, dict):
            schemas[name] = deepcopy(schema)
    return schemas


def _handlers() -> dict[str, ToolHandler]:
    return _registry_handlers()


__all__ = [name for name in globals() if not name.startswith("__")]
