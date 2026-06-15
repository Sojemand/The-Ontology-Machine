from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore, ProgressEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, stable_hash, utc_iso
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.events import ProgressEvent

from .paths import _write_json
from .client_event_snapshot_support import (
    event_belongs_to_phase20_snapshot,
    list_all_client_frontend_events,
)
from .support_runtime import (
    _Phase20EventSink,
    _create_phase20_support_bundle,
    _phase20_expiry,
    _phase20_state_paths,
    _phase20_state_snapshot_identity,
    _phase20_support_only_option,
    _phase20_target_identity,
)

_event_belongs_to_phase20_snapshot = event_belongs_to_phase20_snapshot
_list_all_client_frontend_events = list_all_client_frontend_events


def _build_client_frontend_snapshot_payload(
    run_id: str,
    *,
    state_paths: StatePaths | None = None,
) -> dict[str, Any]:
    paths = _phase20_state_paths(state_paths)
    workflow_store = WorkflowRunStore(paths)
    interaction_store = InteractionRequestStore(paths)
    mirror_store = MirrorEventStore(paths)
    progress_store = ProgressEventStore(paths)
    sink = _Phase20EventSink()
    mirror_service = KernelMirrorEventService(mirror_store)
    interaction_service = KernelUserInteractionService(
        interaction_store=interaction_store,
        mirror_event_service=mirror_service,
        event_sink=sink,
        workflow_run_store=workflow_store,
    )

    interaction_run = workflow_store.create_run(
        "manual_pipeline_run",
        _phase20_target_identity(run_id, "manual_pipeline_run"),
        "phase20_go_live",
    )
    interaction_snapshot = _phase20_state_snapshot_identity(run_id, "manual_pipeline_run")
    progress_event = ProgressEvent.from_dict(
        {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": interaction_run.workflow_run_id,
            "workflow_tool": interaction_run.workflow_tool,
            "step_id": "phase20_runtime_proof",
            "step_label": "Phase 20 Runtime Proof",
            "event_type": "workflow_step",
            "status": "step_started",
            "sequence_index": 1,
            "user_visible_summary": "Kernel progress proof for the Client Frontend bridge is active.",
            "current_state_summary": "Phase 20 runtime-sourced frontend proof drill started.",
            "timestamp": utc_iso(),
        }
    )
    progress_store.append_progress_event(progress_event)
    recovery_event_id = f"rev_{stable_hash(f'{run_id}:recovery_dialog')}"
    recovery_option = {
        "schema_version": "kernel.recovery_option.v1",
        "recovery_id": f"rcv_{stable_hash(f'{run_id}:recovery_dialog')}",
        "recovery_event_id": recovery_event_id,
        "label": "Open recovery dialog",
        "description": "Reopen the Kernel-authored stale-lock recovery dialog.",
        "owner": "agent_tool",
        "recovery_action_type": "reopen_dialog",
        "effect": "open_kernel_recovery_dialog",
        "risk_class": "read_only",
        "target_identity": dict(interaction_run.target_identity),
        "state_snapshot_identity": interaction_snapshot,
        "agent_tool": "kernel_open_recovery_dialog",
        "kernel_dialog_action": "stale_lock_dialog",
        "starts_new_workflow": False,
        "continuation_workflow_tool": None,
        "requires_confirmation": False,
        "expires_at": _phase20_expiry(),
    }
    recovery_dispatch = interaction_service.request_recovery_dialog(
        recovery_dialog_type="stale_lock_dialog",
        recovery_id=str(recovery_option["recovery_id"]),
        workflow_run_id=interaction_run.workflow_run_id,
        function_or_route=interaction_run.workflow_tool,
        target_identity=dict(interaction_run.target_identity),
        state_snapshot_identity=interaction_snapshot,
        user_visible_title="Recovery Available",
        user_visible_summary="A Kernel recovery dialog is available for the runtime proof drill.",
        user_visible_cause="The runtime proof drill is exercising a stale-lock recovery path.",
        recovery_effect="The Kernel can reopen the recovery dialog without exposing hidden values in Agent chat.",
        risk_class="read_only",
        options=(recovery_option,),
        allowed_agent_tools=("kernel_open_recovery_dialog",),
    )

    support_proof = _create_phase20_support_bundle(paths, run_id)
    final_snapshot = _phase20_state_snapshot_identity(run_id, "llm_final_error")
    final_mirror = mirror_service.create_mirror_event(
        event_type="llm_validation_failed_final",
        severity="final_error",
        user_visible_summary="The Kernel could not validate the structured LLM result after retries.",
        current_state_summary="Final LLM validation failure with runtime-sourced support evidence.",
        workflow_run_id=str(support_proof["workflow_run_id"]),
        workflow_tool=str(support_proof["workflow_tool"]),
        user_visible_cause="Structured JSON validation never passed before the retry budget was exhausted.",
        kernel_dialog_state="not_required",
        recovery_options=[
            _phase20_support_only_option(
                recovery_id=f"rcv_{stable_hash(f'{run_id}:llm_final_error')}",
                recovery_event_id=f"rev_{stable_hash(f'{run_id}:llm_final_error')}",
                target_identity=dict(support_proof["target_identity"]),
                state_snapshot_identity=final_snapshot,
            )
        ],
        allowed_agent_tools=["kernel_open_support_bundle"],
        technical_detail_ref={"validation_report_ref": str(support_proof["validation_report_ref"])},
        support_bundle_ref=dict(support_proof["support_bundle_ref"]),
    )

    request_payload = {
        "schema_version": "semantic_control_kernel.client_events_request.v1",
        "host_surface_identity": sink.host_surface_identity,
        "client_instance_id": f"phase20_{stable_hash(run_id)}",
        "client_request_id": f"req_{stable_hash(f'{run_id}:frontend')}",
    }
    all_events, final_cursor = list_all_client_frontend_events(request_payload, state_paths=paths)
    workflow_run_ids = {interaction_run.workflow_run_id, str(support_proof["workflow_run_id"])}
    mirror_event_ids = {
        str(recovery_dispatch.mirror_event.payload["mirror_event_id"]),
        str(final_mirror.payload["mirror_event_id"]),
    }
    interaction_request_ids = {str(recovery_dispatch.request.payload["interaction_request_id"])}
    selected_events = [
        dict(event)
        for event in all_events
        if isinstance(event, Mapping)
        and event_belongs_to_phase20_snapshot(
            event,
            workflow_run_ids=workflow_run_ids,
            mirror_event_ids=mirror_event_ids,
            interaction_request_ids=interaction_request_ids,
        )
    ]
    source_event_refs = {
        "interaction_request_refs": [
            paths.relative_to_state_root(
                paths.pending_interactions_active_dir
                / f"{recovery_dispatch.request.payload['interaction_request_id']}.json"
            )
        ],
        "progress_event_refs": [
            paths.relative_to_state_root(path)
            for path in sorted((paths.events_progress_dir / interaction_run.workflow_run_id).glob("*.json"))
        ],
        "mirror_event_refs": [
            paths.relative_to_state_root(paths.events_mirror_dir / f"{mirror_event_id}.json")
            for mirror_event_id in sorted(mirror_event_ids)
        ],
        "tool_availability_refs": [
            paths.relative_to_state_root(paths.events_tool_availability_dir / f"{mirror_event_id}.json")
            for mirror_event_id in sorted(mirror_event_ids)
            if (paths.events_tool_availability_dir / f"{mirror_event_id}.json").exists()
        ],
    }
    return {
        "schema_version": "semantic_control_kernel.phase20.client_frontend_event_snapshot.v1",
        "go_live_run_id": run_id,
        "source_contract": "kernel_list_client_frontend_events",
        "request": request_payload,
        "selected_cursor": final_cursor,
        "runtime_state_root": "08 - Semantic Control Kernel/state",
        "workflow_run_ids": sorted(workflow_run_ids),
        "mirror_event_ids": sorted(mirror_event_ids),
        "interaction_request_ids": sorted(interaction_request_ids),
        "source_event_refs": source_event_refs,
        "events": selected_events,
    }


def _write_client_frontend_snapshot(
    bundle_root: Path,
    run_id: str,
    *,
    state_paths: StatePaths | None = None,
) -> None:
    payload = _build_client_frontend_snapshot_payload(run_id, state_paths=state_paths)
    _write_json(bundle_root / "client_frontend_event_snapshot.json", payload)
