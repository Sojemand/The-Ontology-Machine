"""Agent permission policy for the local MCP control plane."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .atomic_io import atomic_json_write
from .permission_defaults import AGENT_LEVEL_ENV_FALLBACKS, DEFAULT_POLICY
from .permission_types import PermissionDenied, PermissionPolicyError
from .permission_validation import (
    _required_level_for_tool_validated,
    _tools_for_level_validated,
    configured_tools,
    known_tool_names,
    required_level_for_tool,
    tools_for_level,
    validate_policy,
)

POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "agent_permissions.json"


def default_policy() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_POLICY)


def policy_path() -> Path:
    return POLICY_PATH


def read_policy() -> dict[str, Any]:
    path = policy_path()
    if not path.exists():
        return default_policy()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise PermissionPolicyError(f"Agent-Permission-Policy ist kein gueltiges JSON: {path}") from exc
    return validate_policy(payload)


def write_policy(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_policy(payload)
    path = policy_path()
    atomic_json_write(path, normalized, indent=2, trailing_newline=True)
    return normalized


def assert_tool_allowed(tool_name: str) -> None:
    policy = read_policy()
    if not bool(policy["enabled"]):
        return
    active_level = _active_agent_level_validated(policy)
    allowed = _tools_for_level_validated(policy, active_level)
    if tool_name in allowed:
        return
    required = _required_level_for_tool_validated(policy, tool_name)
    if required:
        raise PermissionDenied(f"{tool_name} braucht mindestens Agent-Level {required}; aktiv ist {active_level}.")
    raise PermissionDenied(f"{tool_name} ist in der MCP-Agent-Policy keiner Agent-Stufe zugeordnet.")


def active_agent_level(policy: dict[str, Any] | None = None) -> str:
    policy = read_policy() if policy is None else validate_policy(policy)
    return _active_agent_level_validated(policy)


def _active_agent_level_validated(policy: dict[str, Any]) -> str:
    configured = str(policy["agent_level_env_var"]).strip()
    candidates = (configured, *AGENT_LEVEL_ENV_FALLBACKS) if configured else AGENT_LEVEL_ENV_FALLBACKS
    requested = ""
    for name in candidates:
        if not name:
            continue
        value = os.environ.get(name)
        if value:
            requested = value.strip()
            break
    level = requested or str(policy["default_agent_level"])
    order = tuple(policy["level_order"])
    if level not in order:
        raise PermissionDenied(f"Unbekanntes Agent-Level: {level}")
    if order.index(level) > order.index(str(policy["maximum_agent_level"])):
        raise PermissionDenied(f"Agent-Level {level} ueberschreitet maximum_agent_level {policy['maximum_agent_level']}.")
    return level


def permission_summary() -> dict[str, Any]:
    policy = read_policy()
    active = _active_agent_level_validated(policy)
    known = known_tool_names()
    allowed = _tools_for_level_validated(policy, active)
    configured = configured_tools(policy)
    return {
        "enabled": bool(policy["enabled"]),
        "policy_path": str(policy_path()),
        "active_agent_level": active,
        "default_agent_level": str(policy["default_agent_level"]),
        "maximum_agent_level": str(policy["maximum_agent_level"]),
        "level_order": list(policy["level_order"]),
        "allowed_tool_count": len(allowed & known),
        "blocked_tool_count": len(known - allowed),
        "unclassified_tools": sorted(known - configured),
    }


def visible_tool_definitions() -> list[dict[str, Any]]:
    from .tool_catalog import tool_definitions
    from .tool_visibility import externally_visible_tool_definitions

    definitions = tool_definitions()
    policy = read_policy()
    if not bool(policy["enabled"]):
        return externally_visible_tool_definitions(definitions)
    allowed = _tools_for_level_validated(policy, _active_agent_level_validated(policy))
    permitted = [tool for tool in definitions if str(tool.get("name") or "").strip() in allowed]
    return externally_visible_tool_definitions(permitted)


__all__ = [name for name in globals() if not name.startswith("_")]
