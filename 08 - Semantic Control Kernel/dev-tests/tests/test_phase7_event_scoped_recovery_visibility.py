from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from semantic_control_kernel import mcp_contract
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_surface_service import AgentToolSurfaceService
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_NAMES
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.events import MirrorEvent


TARGET = {"target_hash": "target_phase7_recovery_visibility"}
SNAPSHOT = {"state_snapshot_id": "ss_phase7_recovery_visibility"}


def test_normal_inventory_excludes_recovery_tools() -> None:
    inventory = AgentToolSurfaceService().build_inventory().to_dict()

    assert inventory["event_scoped_recovery_tools"] == []
    permanent_names = {tool["tool_name"] for tool in inventory["permanent_tools"]}
    assert not permanent_names.intersection(EVENT_SCOPED_RECOVERY_TOOL_NAMES)


def test_absent_or_expired_tool_availability_exposes_no_event_scoped_tools(tmp_path: Path) -> None:
    store = MirrorEventStore(StatePaths.from_state_root(tmp_path / "state"))
    service = AgentToolSurfaceService(store)
    _append_bound_recovery_mirror_event(store, "mirror_expired", ("kernel_open_support_bundle",), _seconds_from_now(-10))

    assert service.list_event_scoped_tools(None) == ()
    assert service.list_event_scoped_tools("missing_mirror") == ()
    assert service.list_event_scoped_tools("mirror_expired") == ()


def test_tool_availability_without_bound_recovery_mirror_exposes_no_event_scoped_tools(tmp_path: Path) -> None:
    store = MirrorEventStore(StatePaths.from_state_root(tmp_path / "state"))
    service = AgentToolSurfaceService(store)
    _append_thin_mirror_event(store, "mirror_thin")
    store.put_tool_availability("mirror_thin", ["kernel_open_support_bundle"], _seconds_from_now(300))

    assert service.list_event_scoped_tools("mirror_thin") == ()


def test_valid_tool_availability_exposes_only_listed_recovery_tools(tmp_path: Path) -> None:
    store = MirrorEventStore(StatePaths.from_state_root(tmp_path / "state"))
    service = AgentToolSurfaceService(store)
    _append_bound_recovery_mirror_event(store, "mirror_active", ("kernel_open_support_bundle",), _seconds_from_now(300))
    store.put_tool_availability(
        "mirror_active",
        ["kernel_open_support_bundle", "kernel_status", "not_a_kernel_tool"],
        _seconds_from_now(300),
    )

    tools = service.list_event_scoped_tools("mirror_active")

    assert tuple(tool.tool_name for tool in tools) == ("kernel_open_support_bundle",)


def test_normal_mcp_tool_listing_does_not_leak_event_scoped_recovery_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(tmp_path / "mcp-state"))

    event_scoped = mcp_contract.list_mcp_tool_definitions("event_scoped_recovery")
    all_tools = mcp_contract.list_mcp_tool_definitions("all")

    assert event_scoped["tool_definitions"] == []
    listed_names = {definition["name"] for definition in all_tools["tool_definitions"]}
    assert not listed_names.intersection(EVENT_SCOPED_RECOVERY_TOOL_NAMES)


def _append_bound_recovery_mirror_event(
    store: MirrorEventStore,
    mirror_event_id: str,
    tools: tuple[str, ...],
    expires_at: str,
) -> None:
    options = RecoveryOptionService().create_options(
        recovery_event_id=f"rev_{mirror_event_id}",
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        expires_at=expires_at,
        safe_tools=tools,
    )
    KernelMirrorEventService(store).create_mirror_event(
        event_type=MirrorEventType.RECOVERY_STATE.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Recovery state is available.",
        current_state_summary="A Kernel recovery event is active.",
        mirror_event_id=mirror_event_id,
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=tools,
        tool_availability_expires_at=expires_at,
    )


def _append_thin_mirror_event(store: MirrorEventStore, mirror_event_id: str) -> None:
    store.append_mirror_event(
        MirrorEvent.from_dict(
            {
                "schema_version": "kernel.mirror_event.v1",
                "mirror_event_id": mirror_event_id,
                "mirror_source": "kernel",
                "is_kernel_auto_call": True,
                "event_type": "recovery_state",
                "severity": "recoverable_error",
                "user_visible_summary": "Recovery state is available.",
                "current_state_summary": "A Kernel recovery event is active.",
            }
        )
    )


def _seconds_from_now(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
