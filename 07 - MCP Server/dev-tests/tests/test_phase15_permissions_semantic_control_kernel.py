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


def test_semantic_control_kernel_permissions_are_one_inherited_transport_surface() -> None:
    config = json.loads((MODULE_ROOT / "config" / "agent_permissions.json").read_text(encoding="utf-8"))
    permanent = set(PERMANENT_AGENT_TOOL_NAMES)

    for policy in (DEFAULT_POLICY, config):
        for level in policy["level_order"]:
            assert tools_for_level(policy, level) & permanent == permanent


def test_legacy_recovery_internal_continuation_and_host_only_names_stay_out_of_permanent_permissions() -> None:
    config = json.loads((MODULE_ROOT / "config" / "agent_permissions.json").read_text(encoding="utf-8"))
    all_default = {tool for level in DEFAULT_POLICY["agent_levels"].values() for tool in level["tools"]}
    all_config = {tool for level in config["agent_levels"].values() for tool in level["tools"]}

    for names in (
        LEGACY_RETIRED_TOOL_NAMES,
        EVENT_SCOPED_RECOVERY_TOOL_NAMES,
        KERNEL_INTERNAL_TOOL_NAMES,
        KERNEL_CONTINUATION_TOOL_NAMES,
        HOST_ONLY_CLIENT_BRIDGE_NAMES,
    ):
        assert set(names).isdisjoint(all_default)
        assert set(names).isdisjoint(all_config)
