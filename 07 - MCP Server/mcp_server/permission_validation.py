from __future__ import annotations

from typing import Any

from .permission_defaults import LEVEL_ORDER, POLICY_SURFACE_ID, SCHEMA_VERSION
from .permission_types import PermissionPolicyError


def validate_policy(payload: object) -> dict[str, Any]:
    data = _mapping(payload, label=POLICY_SURFACE_ID)
    expected_keys = {"schema_version", "enabled", "default_agent_level", "maximum_agent_level", "agent_level_env_var", "reject_unclassified_tools", "level_order", "agent_levels"}
    _require_no_unknown_keys(data, expected_keys, label=POLICY_SURFACE_ID)
    schema_version = _int(data.get("schema_version"), field="schema_version")
    if schema_version != SCHEMA_VERSION:
        raise PermissionPolicyError(f"schema_version muss {SCHEMA_VERSION} sein.")
    level_order = tuple(_string_list(data.get("level_order"), field="level_order"))
    if set(level_order) != set(LEVEL_ORDER):
        raise PermissionPolicyError(f"level_order muss genau diese Agent-Level enthalten: {', '.join(LEVEL_ORDER)}")
    known_names = known_tool_names()
    agent_levels = _agent_levels(data.get("agent_levels"), level_order=level_order, known_names=known_names)
    default_level = _level_name(data.get("default_agent_level"), field="default_agent_level", level_order=level_order)
    maximum_level = _level_name(data.get("maximum_agent_level"), field="maximum_agent_level", level_order=level_order)
    if _rank(default_level, level_order=level_order) > _rank(maximum_level, level_order=level_order):
        raise PermissionPolicyError("default_agent_level darf maximum_agent_level nicht ueberschreiten.")
    normalized = {
        "schema_version": schema_version,
        "enabled": _bool(data.get("enabled"), field="enabled"),
        "default_agent_level": default_level,
        "maximum_agent_level": maximum_level,
        "agent_level_env_var": _agent_env_var(data.get("agent_level_env_var")),
        "reject_unclassified_tools": _bool(data.get("reject_unclassified_tools"), field="reject_unclassified_tools"),
        "level_order": list(level_order),
        "agent_levels": agent_levels,
    }
    _validate_tool_coverage(normalized, known_names=known_names)
    return normalized


def tools_for_level(policy: dict[str, Any], level: str) -> set[str]:
    data = validate_policy(policy)
    return _tools_for_level_validated(data, level)


def _tools_for_level_validated(data: dict[str, Any], level: str) -> set[str]:
    order = tuple(data["level_order"])
    if level not in order:
        raise PermissionPolicyError(f"Unbekanntes Agent-Level: {level}")
    levels = data["agent_levels"]
    collected: set[str] = set()

    def visit(name: str, stack: tuple[str, ...] = ()) -> None:
        if name in stack:
            raise PermissionPolicyError(f"Zyklische Agent-Level-Vererbung: {' -> '.join((*stack, name))}")
        item = levels[name]
        for parent in item["inherits"]:
            visit(parent, (*stack, name))
        collected.update(item["tools"])

    visit(level)
    return collected


def required_level_for_tool(policy: dict[str, Any], tool_name: str) -> str:
    data = validate_policy(policy)
    return _required_level_for_tool_validated(data, tool_name)


def _required_level_for_tool_validated(data: dict[str, Any], tool_name: str) -> str:
    for level in data["level_order"]:
        if tool_name in _tools_for_level_validated(data, str(level)):
            return str(level)
    return ""


def configured_tools(policy: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for item in policy["agent_levels"].values():
        result.update(str(tool) for tool in item["tools"])
    return result


def known_tool_names() -> set[str]:
    from .tool_catalog import tool_names
    return set(tool_names())


def _agent_levels(value: object, *, level_order: tuple[str, ...], known_names: set[str]) -> dict[str, Any]:
    raw = _mapping(value, label="agent_levels")
    if set(raw) != set(level_order):
        raise PermissionPolicyError("agent_levels muss genau die Agent-Level aus level_order enthalten.")
    result: dict[str, Any] = {}
    for level in level_order:
        item = _mapping(raw[level], label=f"agent_levels.{level}")
        _require_no_unknown_keys(item, {"label", "description", "inherits", "tools"}, label=f"agent_levels.{level}")
        inherits = _string_list(item.get("inherits"), field=f"agent_levels.{level}.inherits")
        unknown_inherits = [name for name in inherits if name not in level_order]
        if unknown_inherits:
            raise PermissionPolicyError(f"{level} erbt unbekannte Agent-Level: {', '.join(unknown_inherits)}")
        tools = _string_list(item.get("tools"), field=f"agent_levels.{level}.tools")
        unknown_tools = sorted(set(tools) - known_names)
        if unknown_tools:
            raise PermissionPolicyError(f"{level} enthaelt unbekannte Tools: {', '.join(unknown_tools)}")
        result[level] = {"label": _text(item.get("label"), field=f"agent_levels.{level}.label"), "description": _text(item.get("description"), field=f"agent_levels.{level}.description"), "inherits": inherits, "tools": tools}
    _validate_level_inheritance(result)
    return result


def _validate_level_inheritance(agent_levels: dict[str, Any]) -> None:
    def visit(level: str, stack: tuple[str, ...] = ()) -> None:
        if level in stack:
            raise PermissionPolicyError(f"Zyklische Agent-Level-Vererbung: {' -> '.join((*stack, level))}")
        for parent in agent_levels[level]["inherits"]:
            visit(str(parent), (*stack, level))
    for level in agent_levels:
        visit(level)


def _validate_tool_coverage(policy: dict[str, Any], *, known_names: set[str]) -> None:
    configured = configured_tools(policy)
    unknown = sorted(configured - known_names)
    if unknown:
        raise PermissionPolicyError(f"Agent-Policy enthaelt unbekannte Tools: {', '.join(unknown)}")
    if bool(policy["reject_unclassified_tools"]):
        missing = sorted(known_names - configured)
        if missing:
            raise PermissionPolicyError(f"Agent-Policy klassifiziert nicht alle MCP-Tools: {', '.join(missing)}")


def _rank(level: str, *, level_order: tuple[str, ...]) -> int:
    try:
        return level_order.index(level)
    except ValueError as exc:
        raise PermissionPolicyError(f"Unbekanntes Agent-Level: {level}") from exc


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PermissionPolicyError(f"{label} muss ein JSON-Objekt sein.")
    return dict(value)


def _require_no_unknown_keys(payload: dict[str, Any], expected: set[str], *, label: str) -> None:
    unknown = sorted(set(payload) - expected)
    if unknown:
        raise PermissionPolicyError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = sorted(expected - set(payload))
    if missing:
        raise PermissionPolicyError(f"{label} enthaelt fehlende Felder: {', '.join(missing)}")


def _string_list(value: object, *, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise PermissionPolicyError(f"{field} muss eine String-Liste sein.")
    result = [item.strip() for item in value if item.strip()]
    if len(result) != len(set(result)):
        raise PermissionPolicyError(f"{field} enthaelt doppelte Werte.")
    return result


def _level_name(value: object, *, field: str, level_order: tuple[str, ...]) -> str:
    text = _text(value, field=field)
    if text not in level_order:
        raise PermissionPolicyError(f"{field} muss eines dieser Agent-Level sein: {', '.join(level_order)}")
    return text


def _agent_env_var(value: object) -> str:
    text = _text(value, field="agent_level_env_var")
    if not text.replace("_", "").isalnum():
        raise PermissionPolicyError("agent_level_env_var darf nur Buchstaben, Zahlen und Unterstriche enthalten.")
    return text


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PermissionPolicyError(f"{field} muss ein nicht-leerer String sein.")
    return value.strip()


def _bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise PermissionPolicyError(f"{field} muss true oder false sein.")
    return value


def _int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PermissionPolicyError(f"{field} muss eine Ganzzahl sein.")
    return value


__all__ = ["validate_policy", "tools_for_level", "required_level_for_tool", "configured_tools", "known_tool_names"]
