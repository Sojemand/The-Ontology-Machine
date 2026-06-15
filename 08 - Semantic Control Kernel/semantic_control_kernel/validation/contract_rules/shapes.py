from __future__ import annotations


REQUIRED_FIELD_PATH_RULES: dict[str, tuple[str, ...]] = {
    "kernel.analyze_sample.input.v1": ("source_ref.kind",),
}

FIELD_KIND_RULES: dict[str, dict[str, str]] = {
    "kernel.confirmation_request.v1": {
        "confirmation_scope": "string",
        "expiration_policy": "mapping",
        "required_receipt_shape": "mapping",
        "state_snapshot_identity": "mapping",
        "target_identity": "mapping",
    },
    "kernel.confirmation_receipt.v1": {
        "confirmed_state_snapshot_identity": "mapping",
        "confirmed_target_identity": "mapping",
        "host_surface_identity": "string",
    },
    "kernel.user_interaction_request.v1": {
        "expiration_policy": "mapping",
        "response_shape": "string",
        "state_snapshot_identity": "mapping",
        "target_identity": "mapping",
    },
    "kernel.user_interaction_response.v1": {
        "host_surface_identity": "string",
        "state_snapshot_identity": "mapping",
        "target_identity": "mapping",
    },
    "kernel.client_frontend_event_ack.v1": {
        "accepted": "bool",
        "host_surface_identity": "string",
    },
    "kernel.client_frontend_event_batch.v1": {"events": "list"},
    "kernel.database_merge_reconciliation_receipt.v1": {
        "selected_resolutions": "list",
        "state_snapshot_identity": "mapping",
        "target_identity": "mapping",
    },
    "kernel.operation_receipt.v1": {
        "final_kernel_state": "mapping",
        "input_artifact_refs": "list",
        "output_artifact_refs": "list",
        "target_identity_after": "mapping",
        "target_identity_before": "mapping",
    },
    "kernel.lock_state.v1": {
        "expiry_policy": "mapping",
        "target_identity": "mapping",
    },
    "kernel.workflow_resume_state.v1": {
        "held_lock_refs": "list",
        "pending_confirmation_refs": "list",
        "selected_targets": "list",
        "state_snapshot_identity": "mapping",
    },
    "kernel.resume_option.v1": {
        "target_identity": "mapping",
        "target_summary": "mapping",
    },
    "kernel.workflow_explanation_context.v1": {
        "already_available": "list",
        "changed_artifacts": "list",
        "completed_step_ids_at_run_start": "list",
        "completed_step_ids_this_run": "list",
        "completed_step_ids_total": "list",
        "evidence_refs": "list",
        "performed_this_run": "list",
        "provenance_policy": "mapping",
        "satisfied_precondition_step_ids": "list",
        "unchanged_artifacts": "list",
    },
    "kernel.recovery_option.v1": {
        "state_snapshot_identity": "mapping",
        "target_identity": "mapping",
    },
    "kernel.recovery_receipt.v1": {
        "mutated_refs": "list",
        "selected_recovery_option": "mapping",
        "state_snapshot_identity": "mapping",
        "support_bundle_ref": "mapping",
        "target_identity_after": "mapping",
        "target_identity_before": "mapping",
        "user_confirmation_refs": "list",
        "written_refs": "list",
    },
}

CLIENT_FRONTEND_EVENT_NESTED_CONTRACTS: dict[str, str] = {
    "interaction_request": "kernel.user_interaction_request.v1",
    "mirror_event": "kernel.mirror_event.v1",
    "progress_event": "kernel.progress_event.v1",
}
