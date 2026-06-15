from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel.repository.event_store import MIRROR_EVENT_HARD_CAP, MirrorEventStore
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity
from semantic_control_kernel.validation.contract_validation import KernelContractError
from phase6_mirror_support import SNAPSHOT, TARGET, recovery_options, service as create_service


def test_user_visible_event_and_agent_mirror_share_one_id(tmp_path: Path) -> None:
    service, _mirror_service, mirror_store = create_service(tmp_path)

    result = service.request_interaction(
        interaction_function="use_custom_database_path",
        workflow_run_id="wr_phase6",
        function_or_route="manual_pipeline_run",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Database",
        user_visible_summary="Choose the database path for this workflow.",
    )

    mirror_id = result.mirror_event.payload["mirror_event_id"]
    stored_mirror = mirror_store.get_mirror_event(mirror_id)
    assert result.request.payload["mirror_event_id"] == mirror_id
    assert result.frontend_event.payload["mirror_event_id"] == mirror_id
    assert stored_mirror.payload["mirror_source"] == "kernel"
    assert stored_mirror.payload["is_kernel_auto_call"] is True
    assert stored_mirror.payload["allowed_agent_tools"] == []


def test_normal_dialog_options_do_not_become_agent_recovery_options(tmp_path: Path) -> None:
    service, _mirror_service, mirror_store = create_service(tmp_path)

    result = service.request_interaction(
        interaction_function="use_current_active_database",
        workflow_run_id="wr_phase6",
        function_or_route="manual_pipeline_run",
        target_identity={
            **TARGET,
            "database_id": "dbid_phase6",
        },
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Database Source",
        user_visible_summary="Choose whether to use the active database.",
        options=(
            {
                "choice_id": "current_active_database",
                "label": "Use current active database",
            },
        ),
    )

    stored_mirror = mirror_store.get_mirror_event(result.mirror_event.payload["mirror_event_id"])
    assert result.frontend_event.payload["interaction_request"]["options"][0]["choice_id"] == "current_active_database"
    assert "recovery_options" not in stored_mirror.payload
    assert stored_mirror.payload["allowed_agent_tools"] == []


def test_auto_call_truth_table_for_passive_snapshot_vs_injected_events(tmp_path: Path) -> None:
    _interaction_service, mirror_service, _mirror_store = create_service(tmp_path)
    options, expires_at = recovery_options()

    passive = mirror_service.create_passive_snapshot(
        event_type=MirrorEventType.PROGRESS.value,
        severity=MirrorSeverity.INFO.value,
        user_visible_summary="Kernel status snapshot.",
        current_state_summary="No active workflow.",
    )
    injected = mirror_service.create_mirror_event(
        event_type=MirrorEventType.RECOVERY_STATE.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Recovery is available.",
        current_state_summary="A recovery option is scoped to this event.",
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=("kernel_open_recovery_dialog",),
        tool_availability_expires_at=expires_at,
    )

    assert passive.payload["is_kernel_auto_call"] is False
    assert passive.payload["allowed_agent_tools"] == []
    assert injected.payload["is_kernel_auto_call"] is True
    assert injected.payload["allowed_agent_tools"] == ["kernel_open_recovery_dialog"]


def test_event_scoped_tools_are_rejected_for_normal_interaction_requests(tmp_path: Path) -> None:
    service, _mirror_service, _mirror_store = create_service(tmp_path)

    with pytest.raises(KernelContractError):
        service.request_interaction(
            interaction_function="use_custom_database_path",
            workflow_run_id="wr_phase6",
            function_or_route="manual_pipeline_run",
            target_identity=TARGET,
            state_snapshot_identity=SNAPSHOT,
            user_visible_title="Choose Database",
            user_visible_summary="Choose the database path for this workflow.",
            allowed_agent_tools=("kernel_open_recovery_dialog",),
        )


def test_event_scoped_tools_require_kernel_recovery_options(tmp_path: Path) -> None:
    _interaction_service, mirror_service, _mirror_store = create_service(tmp_path)

    with pytest.raises(KernelContractError):
        mirror_service.create_mirror_event(
            event_type=MirrorEventType.RECOVERY_STATE.value,
            severity=MirrorSeverity.RECOVERABLE_ERROR.value,
            user_visible_summary="Recovery is available.",
            current_state_summary="A recovery option is missing.",
            allowed_agent_tools=("kernel_open_recovery_dialog",),
        )


def test_event_scoped_tools_require_full_recovery_option_contract(tmp_path: Path) -> None:
    _interaction_service, mirror_service, _mirror_store = create_service(tmp_path)

    with pytest.raises(KernelContractError):
        mirror_service.create_mirror_event(
            event_type=MirrorEventType.RECOVERY_STATE.value,
            severity=MirrorSeverity.RECOVERABLE_ERROR.value,
            user_visible_summary="Recovery is available.",
            current_state_summary="A thin recovery option is invalid.",
            recovery_options=[{"recovery_id": "rcv_phase6", "label": "Thin option", "agent_tool": "kernel_open_recovery_dialog"}],
            allowed_agent_tools=("kernel_open_recovery_dialog",),
        )


def test_mirror_event_store_prunes_to_hard_cap_and_drops_stale_tool_availability(tmp_path: Path) -> None:
    _interaction_service, mirror_service, mirror_store = create_service(tmp_path)
    options, expires_at = recovery_options()

    total_events = MIRROR_EVENT_HARD_CAP + 3
    for index in range(total_events):
        mirror_id = f"mev_cap_{index:04d}"
        mirror_service.create_mirror_event(
            mirror_event_id=mirror_id,
            event_type=MirrorEventType.RECOVERY_STATE.value,
            severity=MirrorSeverity.RECOVERABLE_ERROR.value,
            user_visible_summary=f"Recovery event {index}",
            current_state_summary=f"state {index}",
            recovery_options=[option.to_dict() for option in options],
            allowed_agent_tools=("kernel_open_recovery_dialog",),
            tool_availability_expires_at=expires_at,
        )

    mirror_paths = sorted(paths.name for paths in mirror_store.paths.events_mirror_dir.glob("*.json"))
    tool_paths = sorted(paths.name for paths in mirror_store.paths.events_tool_availability_dir.glob("*.json"))

    assert len(mirror_paths) == MIRROR_EVENT_HARD_CAP
    assert len(tool_paths) == MIRROR_EVENT_HARD_CAP
    assert "mev_cap_0000.json" not in mirror_paths
    assert "mev_cap_0001.json" not in mirror_paths
    assert f"mev_cap_{total_events - 1:04d}.json" in mirror_paths
    assert "mev_cap_0000.json" not in tool_paths
    assert "mev_cap_0001.json" not in tool_paths
