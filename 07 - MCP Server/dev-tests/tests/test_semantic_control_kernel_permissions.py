from __future__ import annotations

import json
from pathlib import Path

from mcp_server.permission_defaults import DEFAULT_POLICY
from mcp_server.permission_validation import tools_for_level
from mcp_server.semantic_control_kernel_visibility import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    HOST_ONLY_CLIENT_BRIDGE_NAMES,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    LEGACY_RETIRED_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_permission_defaults_and_config_include_only_permanent_kernel_agent_tools() -> None:
    config = json.loads((MODULE_ROOT / "config" / "agent_permissions.json").read_text(encoding="utf-8"))
    default_levels = DEFAULT_POLICY["agent_levels"]
    config_levels = config["agent_levels"]

    all_default = {tool for level in default_levels.values() for tool in level["tools"]}
    all_config = {tool for level in config_levels.values() for tool in level["tools"]}

    for level in DEFAULT_POLICY["level_order"]:
        assert tools_for_level(DEFAULT_POLICY, level) & set(PERMANENT_AGENT_TOOL_NAMES) == set(PERMANENT_AGENT_TOOL_NAMES)
        assert tools_for_level(config, level) & set(PERMANENT_AGENT_TOOL_NAMES) == set(PERMANENT_AGENT_TOOL_NAMES)
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(all_default)
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(all_config)
    assert set(EVENT_SCOPED_RECOVERY_TOOL_NAMES).isdisjoint(all_default)
    assert set(EVENT_SCOPED_RECOVERY_TOOL_NAMES).isdisjoint(all_config)
    assert set(KERNEL_INTERNAL_TOOL_NAMES).isdisjoint(all_default)
    assert set(KERNEL_INTERNAL_TOOL_NAMES).isdisjoint(all_config)
    assert set(KERNEL_CONTINUATION_TOOL_NAMES).isdisjoint(all_default)
    assert set(KERNEL_CONTINUATION_TOOL_NAMES).isdisjoint(all_config)
    assert set(HOST_ONLY_CLIENT_BRIDGE_NAMES).isdisjoint(all_default)
    assert set(HOST_ONLY_CLIENT_BRIDGE_NAMES).isdisjoint(all_config)
