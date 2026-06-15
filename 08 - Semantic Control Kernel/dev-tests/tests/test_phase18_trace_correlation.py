from __future__ import annotations

import json
from semantic_control_kernel.debug.adapter_diagnostics import AdapterDiagnosticRecorder
from semantic_control_kernel.debug.llm_diagnostics import LLMAttemptDiagnosticRecorder
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.confirmation_store import ConfirmationRequestStore
from semantic_control_kernel.repository.event_store import MirrorEventStore, ProgressEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryResultStatus, RecoveryStateClass
from semantic_control_kernel.types.events import ProgressEvent, UserInteractionRequest, UserInteractionResponse
from semantic_control_kernel.types.receipts import ConfirmationReceipt, ConfirmationRequest, OperationReceipt

from phase18_trace_support import fixture as _fixture


def test_trace_link_store_lists_complete_chain_by_workflow_and_trace(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "trace_target"},
        "trace_test",
    )
    progress_store = ProgressEventStore(paths)
    mirror_store = MirrorEventStore(paths)
    trace_store = TraceLinkStore(paths)
    receipt_store = ReceiptStore(paths)
    confirmation_store = ConfirmationRequestStore(paths)
    interaction_store = InteractionRequestStore(paths)
    recovery_store = RecoveryEventStore(paths)

    progress_store.append_progress_event(
        ProgressEvent.from_dict(
            {
                "schema_version": "kernel.progress_event.v1",
                "workflow_run_id": run.workflow_run_id,
                "workflow_tool": run.workflow_tool,
                "sequence_index": 1,
                "event_type": "workflow_step",
                "status": "step_started",
                "step_id": "pipeline_run",
                "step_label": "Pipeline run",
                "timestamp": "2026-05-06T09:00:00Z",
                "user_visible_summary": "Pipeline run started.",
                "current_state_summary": "running",
                "receipt_refs": [],
            }
        )
    )
    mirror = KernelMirrorEventService(mirror_store).create_mirror_event(
        event_type=MirrorEventType.RECOVERY_STATE.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Kernel mirror event.",
        current_state_summary="running",
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        recovery_options=[],
        allowed_agent_tools=[],
    )

    interaction_request = _fixture("kernel.user_interaction_request.v1")
    interaction_request["interaction_request_id"] = "irq_trace"
    interaction_request["workflow_run_id"] = run.workflow_run_id
    interaction_request["target_identity"] = {"target_hash": "trace_target"}
    interaction_request["state_snapshot_identity"] = {"state_snapshot_id": "ss_trace"}
    interaction_request["expiration_policy"]["expires_at"] = "2099-01-01T00:00:00Z"
    interaction_store.put_pending_interaction(UserInteractionRequest.from_dict(interaction_request))

    interaction_response = _fixture("kernel.user_interaction_response.v1")
    interaction_response["interaction_request_id"] = "irq_trace"
    interaction_response["interaction_response_id"] = "irs_trace"
    interaction_response["target_identity"] = {"target_hash": "trace_target"}
    interaction_response["state_snapshot_identity"] = {"state_snapshot_id": "ss_trace"}
    interaction_store.submit_interaction_response(UserInteractionResponse.from_dict(interaction_response))

    confirmation_request = _fixture("kernel.confirmation_request.v1")
    confirmation_request["confirmation_request_id"] = "cfr_trace"
    confirmation_request["workflow_run_id"] = run.workflow_run_id
    confirmation_request["target_identity"] = {"target_hash": "trace_target"}
    confirmation_request["state_snapshot_identity"] = {"state_snapshot_id": "ss_trace"}
    confirmation_store.put_pending_request(ConfirmationRequest.from_dict(confirmation_request))

    confirmation_receipt = _fixture("kernel.confirmation_receipt.v1")
    confirmation_receipt["confirmation_receipt_id"] = "cpt_trace"
    confirmation_receipt["confirmation_request_id"] = "cfr_trace"
    confirmation_receipt["confirmed_target_identity"] = {"target_hash": "trace_target"}
    confirmation_receipt["confirmed_state_snapshot_identity"] = {"state_snapshot_id": "ss_trace"}
    confirmation_receipt_contract = ConfirmationReceipt.from_dict(confirmation_receipt)
    receipt_store.append_confirmation_receipt(confirmation_receipt_contract)
    confirmation_store.consume_confirmation_receipt(confirmation_receipt_contract)

    operation_receipt = _fixture("kernel.operation_receipt.v1")
    operation_receipt["operation_receipt_id"] = "opr_trace"
    operation_receipt["workflow_run_id"] = run.workflow_run_id
    operation_receipt["target_identity_after"] = {"target_hash": "trace_target"}
    receipt_store.append_operation_receipt(OperationReceipt.from_dict(operation_receipt))

    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    recovery_options = RecoveryOptionService().create_options(
        recovery_event_id="rev_trace",
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        target_identity={"target_hash": "trace_target"},
        state_snapshot_identity={"state_snapshot_id": "ss_trace"},
        expires_at=expires_at,
        safe_tools=("kernel_open_recovery_dialog",),
    )
    recovery_event = recovery_store.put_recovery_event(
        {
            "allowed_agent_tools": ["kernel_open_recovery_dialog"],
            "blocked_functions": ["pipeline_run"],
            "cause_code": "target_identity_changed",
            "created_at": utc_iso(),
            "detected_by": "phase18_trace_test",
            "expires_at": expires_at,
            "failed_kernel_step": "trace_step",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_trace",
            "recovery_options": [option.to_dict() for option in recovery_options],
            "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            "schema_version": "kernel.recovery_event.v1",
            "state_snapshot_identity": {"state_snapshot_id": "ss_trace"},
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": {"target_hash": "trace_target"},
            "user_visible_cause": "Target changed.",
            "workflow_run_id": run.workflow_run_id,
            "workflow_tool": run.workflow_tool,
        }
    )
    recovery_store.append_recovery_receipt(
        recovery_event=recovery_event,
        recovery_id=recovery_options[0].payload["recovery_id"],
        result_status=RecoveryResultStatus.APPLIED.value,
        selected_recovery_option=recovery_options[0].to_dict(),
    )

    adapter_diagnostic = AdapterDiagnosticRecorder(paths).record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_trace",
        status="ok",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_trace/request.json",
        response_ref="adapter_calls/adc_trace/owner_response.raw.json",
    )
    llm_diagnostic = LLMAttemptDiagnosticRecorder(paths).record_failed_attempt(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        analysis_run_id="ana_trace",
        llm_function_name="analyze_samples",
        attempt_index=1,
        max_attempts=3,
        attempted_schema="kernel.sample_analysis.v1",
        parse_status="invalid_json",
        validation_status="failed",
        validation_error_summary="Missing required keys.",
        artifact_refs={"prompt_snapshot_ref": "sample/a/1/prompt.json"},
    )
    support_ref = SupportBundleStore(paths).write_support_bundle(
        category="support_only_unrecoverable",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_trace",
        summary="Trace correlation support bundle.",
        workflow_tool=run.workflow_tool,
        included_refs=[{"adapter_call_id": adapter_diagnostic["adapter_call_id"]}],
    )

    workflow_links = trace_store.list_links_for_workflow(run.workflow_run_id)
    trace_id = trace_store.get_trace_context(run.workflow_run_id)["trace_id"]
    trace_links = trace_store.list_links_for_trace(trace_id)
    kinds = {item["object_kind"] for item in workflow_links}
    bundle_links = json.loads((paths.support_bundles_dir / support_ref.payload["support_bundle_id"] / "trace_links.json").read_text(encoding="utf-8"))["links"]

    assert kinds >= {
        "workflow_run",
        "progress_event",
        "mirror_event",
        "interaction_request",
        "interaction_response",
        "confirmation_request",
        "confirmation_receipt",
        "recovery_event",
        "recovery_option",
        "recovery_receipt",
        "operation_receipt",
        "adapter_call_diagnostic",
        "llm_attempt_diagnostic",
        "llm_attempt_artifact",
        "support_bundle",
    }
    assert len(workflow_links) == len(trace_links)
    assert any(link["object_kind"] == "support_bundle" and link["object_id"] == support_ref.payload["support_bundle_id"] for link in bundle_links)
    assert support_ref.payload["support_bundle_id"]
    assert llm_diagnostic["llm_attempt_id"]
