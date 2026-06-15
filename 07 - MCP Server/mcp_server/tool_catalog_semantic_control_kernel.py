from __future__ import annotations

import os
from copy import deepcopy
from functools import lru_cache
from typing import Any

from .semantic_control_kernel_client import BRIDGE_CONFIG_PATH, SemanticControlKernelClient
from .semantic_control_kernel_visibility import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES as SEMANTIC_CONTROL_KERNEL_EVENT_SCOPED_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES as SEMANTIC_CONTROL_KERNEL_INTERNAL_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES as SEMANTIC_CONTROL_KERNEL_PERMANENT_TOOL_NAMES,
)


def semantic_control_kernel_tools() -> list[dict[str, Any]]:
    return _copy_tools(_cached_mcp_tool_definitions("permanent_agent", semantic_control_kernel_catalog_cache_token()))


def semantic_control_kernel_event_scoped_tools(
    mirror_event_id: str,
    *,
    recovery_event_id: str | None = None,
    state_snapshot_id: str | None = None,
    client_request_id: str | None = None,
) -> list[dict[str, Any]]:
    if not recovery_event_id or not state_snapshot_id:
        return []
    payload = SemanticControlKernelClient().list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": recovery_event_id,
            "state_snapshot_id": state_snapshot_id,
            "host_surface_identity": "mcp_server_client_frontend_bridge",
            "client_request_id": client_request_id or "mcp_server_client_frontend_bridge",
        }
    )
    return list(payload.get("tool_definitions") or [])


def semantic_control_kernel_internal_tools() -> list[dict[str, Any]]:
    return _copy_tools(_cached_mcp_tool_definitions("kernel_internal", semantic_control_kernel_catalog_cache_token()))


def semantic_control_kernel_catalog_cache_token() -> tuple[object, ...]:
    return (
        id(SemanticControlKernelClient.list_mcp_tool_definitions),
        _bridge_config_fingerprint(),
        os.environ.get("SEMANTIC_CONTROL_KERNEL_MODULE_ROOT", ""),
    )


def clear_semantic_control_kernel_tool_cache() -> None:
    _cached_mcp_tool_definitions.cache_clear()


@lru_cache(maxsize=8)
def _cached_mcp_tool_definitions(scope: str, cache_token: tuple[object, ...]) -> tuple[dict[str, Any], ...]:
    payload = SemanticControlKernelClient().list_mcp_tool_definitions(scope)
    return tuple(deepcopy(list(payload.get("tool_definitions") or [])))


def _copy_tools(tools: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [deepcopy(tool) for tool in tools]


def _bridge_config_fingerprint() -> tuple[int | None, int | None]:
    try:
        stat = BRIDGE_CONFIG_PATH.stat()
    except OSError:
        return (None, None)
    return (stat.st_mtime_ns, stat.st_size)
