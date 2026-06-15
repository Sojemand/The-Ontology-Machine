from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.services.agent_tool_surface_service import AgentToolSurfaceService
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_NAMES

from test_phase13_allowed_agent_tools_lifecycle import _active_event


def test_permanent_agent_tool_list_excludes_all_recovery_tools() -> None:
    inventory = AgentToolSurfaceService().build_inventory().to_dict()
    permanent = {tool["tool_name"] for tool in inventory["permanent_tools"]}

    assert not permanent.intersection(EVENT_SCOPED_RECOVERY_TOOL_NAMES)
    assert inventory["event_scoped_recovery_tools"] == []


def test_recovery_tools_appear_only_for_matching_mirror_event_and_disappear_after_resolution(tmp_path: Path) -> None:
    _paths, recovery_store, mirror_store, event, _option = _active_event(tmp_path, tools=("kernel_open_recovery_dialog",))
    service = AgentToolSurfaceService(mirror_store)

    assert [tool.tool_name for tool in service.list_event_scoped_tools(event.payload["mirror_event_id"])] == ["kernel_open_recovery_dialog"]
    assert service.list_event_scoped_tools("another_mirror_event") == ()

    recovery_store.update_status(event.payload["recovery_event_id"], "resolved")
    mirror_store.mark_event_scoped_tools_expired(event.payload["mirror_event_id"], "recovery_resolved")

    assert service.list_event_scoped_tools(event.payload["mirror_event_id"]) == ()
