from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.testing.fakes.fake_client_frontend_sink import FakeClientFrontendSink

TARGET = {"target_hash": "tgt_phase6", "database_path_hash": "db_phase6"}
SNAPSHOT = {"state_snapshot_id": "ss_phase6"}
EXPIRES_AT = "2026-05-05T00:30:00Z"


def service_for(tmp_path: Path) -> KernelUserInteractionService:
    paths = StatePaths.from_state_root(tmp_path / "state")
    return KernelUserInteractionService(
        interaction_store=InteractionRequestStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        event_sink=FakeClientFrontendSink(),
    )


def service_with_paths(tmp_path: Path) -> tuple[KernelUserInteractionService, StatePaths, MirrorEventStore]:
    paths = StatePaths.from_state_root(tmp_path / "state")
    mirror_store = MirrorEventStore(paths)
    return (
        KernelUserInteractionService(
            interaction_store=InteractionRequestStore(paths),
            mirror_event_service=KernelMirrorEventService(mirror_store),
            event_sink=FakeClientFrontendSink(),
        ),
        paths,
        mirror_store,
    )


def recovery_option(
    recovery_id: str,
    recovery_dialog_type: str,
    *,
    label: str,
    description: str,
    risk_class: str = "read_only",
    agent_tool: str | None = None,
    owner: str = "kernel_dialog",
    recovery_action_type: str = "reopen_dialog",
    effect: str = "open_kernel_recovery_dialog",
    extra: dict | None = None,
) -> dict:
    payload = {
        "schema_version": "kernel.recovery_option.v1",
        "recovery_id": recovery_id,
        "recovery_event_id": f"rev_{recovery_id}",
        "label": label,
        "description": description,
        "owner": owner,
        "recovery_action_type": recovery_action_type,
        "effect": effect,
        "risk_class": risk_class,
        "target_identity": TARGET,
        "state_snapshot_identity": SNAPSHOT,
        "agent_tool": agent_tool,
        "kernel_dialog_action": recovery_dialog_type,
        "starts_new_workflow": False,
        "continuation_workflow_tool": None,
        "requires_confirmation": False,
        "expires_at": EXPIRES_AT,
    }
    if extra:
        payload.update(extra)
    return payload


def value_for_recovery_type(recovery_dialog_type: str) -> dict:
    if recovery_dialog_type in {"path_reselection_dialog", "overwrite_decision_dialog", "rebind_database_artifact_tree_dialog"}:
        return {"path_value": "C:/tmp/reselected"}
    if recovery_dialog_type in {"merge_reconciliation_dialog", "stale_lock_dialog"}:
        return {"choice_id": "inspect_status"}
    if recovery_dialog_type == "partial_pipeline_run_recovery_dialog":
        return {}
    return {"confirmation_decision": "confirmed"}
