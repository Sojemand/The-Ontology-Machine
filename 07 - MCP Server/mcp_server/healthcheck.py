"""Owner-local readiness checks for the MCP Server module."""

from __future__ import annotations

import importlib
from typing import Any

from . import support_monitor
from .permissions import permission_summary, read_policy, visible_tool_definitions
from .runtime_preflight import check_runtime_manifest
from .tool_catalog import tool_definitions


def run_healthcheck(*, strict_runtime: bool = False) -> dict[str, Any]:
    runtime = check_runtime_manifest(strict_executable=strict_runtime)
    catalog = _tool_catalog_check()
    permissions = _permission_policy_check()
    startup = _startup_check()
    support = _support_monitor_check()
    healthy = all(
        bool(section.get("ok"))
        for section in (runtime, catalog, permissions, startup, support)
    )
    return {
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "message": _message(runtime, catalog, permissions, startup, support),
        "server_mode": "local_desktop_stdio_only",
        "transport": "stdio",
        "network_surface": "none",
        "runtime": runtime,
        "tool_count": catalog["tool_count"],
        "tool_catalog": catalog,
        "permission_policy": permissions,
        "agent_permissions": permissions.get("summary", {}),
        "startup": startup,
        "support_monitor": support,
    }


def _tool_catalog_check() -> dict[str, Any]:
    errors: list[str] = []
    tools = tool_definitions()
    names = [str(tool.get("name") or "").strip() for tool in tools]
    missing_names = [index for index, name in enumerate(names) if not name]
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    schema_errors = _schema_errors(tools)
    if not tools:
        errors.append("Tool-Katalog ist leer.")
    if missing_names:
        errors.append(f"Tool-Katalog enthaelt namenlose Eintraege: {missing_names}")
    if duplicates:
        errors.append(f"Tool-Katalog enthaelt doppelte Toolnamen: {', '.join(duplicates)}")
    errors.extend(schema_errors)
    return {
        "ok": not errors,
        "tool_count": len(tools),
        "duplicate_names": duplicates,
        "schema_errors": schema_errors,
        "errors": errors,
    }


def _schema_errors(tools: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for tool in tools:
        name = str(tool.get("name") or "<unnamed>")
        schema = tool.get("inputSchema")
        if not isinstance(schema, dict):
            errors.append(f"{name}: inputSchema fehlt oder ist kein Objekt.")
            continue
        if schema.get("type") != "object":
            errors.append(f"{name}: inputSchema.type muss object sein.")
        if not isinstance(schema.get("properties"), dict):
            errors.append(f"{name}: inputSchema.properties muss ein Objekt sein.")
        if not isinstance(schema.get("required"), list):
            errors.append(f"{name}: inputSchema.required muss eine Liste sein.")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{name}: inputSchema.additionalProperties muss false sein.")
    return errors


def _permission_policy_check() -> dict[str, Any]:
    try:
        policy = read_policy()
        summary = permission_summary()
    except Exception as exc:
        return {"ok": False, "errors": [str(exc)]}
    unclassified = list(summary.get("unclassified_tools") or [])
    reject_unclassified = bool(policy["reject_unclassified_tools"])
    return {
        "ok": reject_unclassified and not unclassified,
        "enabled": bool(policy["enabled"]),
        "policy_path": summary["policy_path"],
        "active_agent_level": summary["active_agent_level"],
        "default_agent_level": summary["default_agent_level"],
        "maximum_agent_level": summary["maximum_agent_level"],
        "reject_unclassified_tools": reject_unclassified,
        "fail_closed": reject_unclassified and not unclassified,
        "unclassified_tools": unclassified,
        "summary": summary,
        "errors": [] if reject_unclassified and not unclassified else ["Permission-Policy ist nicht fail-closed."],
    }


def _startup_check() -> dict[str, Any]:
    errors: list[str] = []
    server_importable = _module_importable("mcp_server.server", errors)
    protocol_importable = _module_importable("mcp_server.protocol", errors)
    try:
        visible_tools = visible_tool_definitions()
    except Exception as exc:
        visible_tools = []
        errors.append(f"tools/list ist nicht startbereit: {exc}")
    return {
        "ok": server_importable and protocol_importable and not errors,
        "stdio_server_importable": server_importable,
        "protocol_importable": protocol_importable,
        "tools_list_ready": not any(error.startswith("tools/list") for error in errors),
        "visible_tool_count": len(visible_tools),
        "network_surface": "none",
        "errors": errors,
    }


def _support_monitor_check() -> dict[str, Any]:
    try:
        value = support_monitor.support_surface_value()
    except Exception as exc:
        return {"ok": False, "errors": [str(exc)]}
    return {"ok": True, "errors": [], **value}


def _module_importable(module_name: str, errors: list[str]) -> bool:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        errors.append(f"{module_name} ist nicht importierbar: {exc}")
        return False
    return True


def _message(*sections: dict[str, Any]) -> str:
    errors: list[str] = []
    for section in sections:
        errors.extend(str(item) for item in section.get("errors", []) if str(item).strip())
        errors.extend(str(item) for item in section.get("missing_required_files", []) if str(item).strip())
    return "; ".join(errors)


__all__ = ["run_healthcheck"]
