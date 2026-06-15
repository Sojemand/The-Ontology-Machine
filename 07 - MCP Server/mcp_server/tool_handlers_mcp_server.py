from __future__ import annotations

from .edit_contract import workflow
from .edit_contract.types import SURFACE_IDS
from .healthcheck import run_healthcheck
from .tool_handler_deps import *

_MCP_SURFACE_IDS = set(SURFACE_IDS)


def mcp_server_describe_surfaces(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, set(), "mcp_server.describe_surfaces")
    return workflow.describe(module_root=None)


def mcp_server_read_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id"}, "mcp_server.read_surface")
    surface_id = _mcp_surface_id(arguments)
    return _local_edit_response(lambda: workflow.read(surface_id, module_root=None))


def mcp_server_validate_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "mcp_server.validate_surface")
    surface_id = _mcp_surface_id(arguments)
    value = _required_mapping(arguments, "value")
    return _local_edit_response(lambda: workflow.validate(surface_id, value, module_root=None))


def mcp_server_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"strict_runtime"}, "mcp_server.healthcheck")
    return run_healthcheck(strict_runtime=_optional_bool(arguments, "strict_runtime", default=False))


def _mcp_surface_id(arguments: dict[str, Any]) -> str:
    surface_id = _required_text(arguments, "surface_id")
    if not surface_id.startswith("mcp_server."):
        raise ToolFailure(
            "mcp_server.* Edit-Tools lesen oder validieren nur MCP-eigene Surfaces; "
            "nutze die dedizierten Owner-Edit-Tools fuer fremde Owner."
        )
    if surface_id not in _MCP_SURFACE_IDS:
        raise ToolFailure(f"Unbekannte MCP-Server-Surface: {surface_id}")
    return surface_id


def _local_edit_response(reader) -> dict[str, Any]:
    try:
        return reader()
    except ValueError as exc:
        raise ToolFailure(str(exc)) from exc


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")


__all__ = [name for name in globals() if not name.startswith("__")]
