from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.attach_state_store import ActiveArtifactTreeRefStore, AttachStateStore
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.event_store import MirrorEventStore, ProgressEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.types.enums import AttachPointerOwner, ProgressEventType
from semantic_control_kernel.types.events import MirrorEvent, ProgressEvent
from semantic_control_kernel.types.receipts import OperationReceipt
from semantic_control_kernel.types.state import DatabaseArtifactBinding, SemanticReleaseAttachState
from semantic_control_kernel.workflows.database_creation.execution_state import DatabaseCreationExecution


class CreationStateRepository:
    def __init__(self, state_root: str | Path) -> None:
        self.paths = StatePaths.from_state_root(state_root)
        self.paths.ensure_layout()
        self.receipts = ReceiptStore(self.paths)
        self.progress = ProgressEventStore(self.paths)
        self.mirrors = MirrorEventStore(self.paths)
        self.artifact_refs = ActiveArtifactTreeRefStore(self.paths)
        self.bindings = DatabaseArtifactBindingRegistry(self.paths)
        self.attach_states = AttachStateStore(self.paths)

    def append_progress(
        self,
        execution: DatabaseCreationExecution,
        *,
        step_id: str,
        status: str,
        summary: str,
        event_type: str = ProgressEventType.WORKFLOW_STEP.value,
        artifact_refs: Sequence[Mapping[str, Any]] | None = None,
        receipt_refs: Sequence[Mapping[str, Any]] | None = None,
    ) -> ProgressEvent:
        execution._sequence_index += 1
        payload = {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": execution.workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": step_id,
            "step_label": step_id,
            "event_type": event_type,
            "status": status,
            "sequence_index": execution._sequence_index,
            "user_visible_summary": summary,
            "current_state_summary": execution.final_state,
            "timestamp": utc_iso(),
            "artifact_refs": [dict(item) for item in artifact_refs or ()],
            "receipt_refs": [dict(item) for item in receipt_refs or ()],
        }
        event = ProgressEvent.from_dict(payload)
        self.progress.append_progress_event(event)
        execution.progress_events.append(event.to_dict())
        return event

    def append_operation_receipt(
        self,
        execution: DatabaseCreationExecution,
        *,
        function_name: str,
        final_kernel_state: str,
        input_artifact_refs: Sequence[Mapping[str, Any]] | None = None,
        output_artifact_refs: Sequence[Mapping[str, Any]] | None = None,
        pipeline_adapter_receipts: Sequence[Mapping[str, Any]] | None = None,
    ) -> OperationReceipt:
        payload = {
            "schema_version": OperationReceipt.SCHEMA_VERSION,
            "operation_receipt_id": generate_id("operation_receipt_id"),
            "function_name": function_name,
            "workflow_run_id": execution.workflow_run_id,
            "target_identity_before": execution.target_identity,
            "target_identity_after": execution.target_identity,
            "input_artifact_refs": [dict(item) for item in input_artifact_refs or ()],
            "output_artifact_refs": [dict(item) for item in output_artifact_refs or ()],
            "final_kernel_state": {"state": final_kernel_state},
            "created_at": utc_iso(),
        }
        if pipeline_adapter_receipts:
            payload["pipeline_adapter_receipts"] = [dict(item) for item in pipeline_adapter_receipts]
        receipt = OperationReceipt.from_dict(payload)
        self.receipts.append_operation_receipt(receipt)
        execution.operation_receipts.append(receipt.to_dict())
        return receipt

    def append_mirror(
        self,
        execution: DatabaseCreationExecution,
        *,
        event_type: str,
        severity: str,
        summary: str,
        current_state_summary: str | None = None,
        allowed_agent_tools: Sequence[str] = (),
        extra: Mapping[str, Any] | None = None,
    ) -> MirrorEvent:
        payload = {
            "schema_version": MirrorEvent.SCHEMA_VERSION,
            "mirror_event_id": generate_id("mirror_event_id"),
            "mirror_source": "kernel",
            "is_kernel_auto_call": True,
            "event_type": event_type,
            "severity": severity,
            "user_visible_summary": summary,
            "current_state_summary": current_state_summary or execution.final_state,
            "workflow_run_id": execution.workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "kernel_dialog_state": "not_required",
            "allowed_agent_tools": list(allowed_agent_tools),
        }
        if extra:
            payload.update(dict(extra))
        event = MirrorEvent.from_dict(payload)
        self.mirrors.append_mirror_event(event)
        execution.mirror_events.append(event.to_dict())
        return event

    def store_active_artifact_tree(self, execution: DatabaseCreationExecution, validation_receipt_id: str) -> None:
        if execution.target is None:
            raise ValueError("Cannot store Artifact Tree without a target.")
        target = execution.target
        ref_payload = {
            "schema_version": "repository.active_artifact_tree_ref.v1",
            "artifact_root_path": target.artifact_root_path,
            "artifact_root_path_hash": target.path_hashes["artifact_root_path_hash"],
            "folder_contract_version": "phase9.database_creation.v1",
            "canonical_paths": target.canonical_paths(),
            "target_identity": target.target_identity,
            "validation_receipt_id": validation_receipt_id,
            "validated_at": utc_iso(),
            "status": "active",
        }
        self.artifact_refs.put_verified_artifact_tree_ref(ref_payload, evidence_refs=[validation_receipt_id])

    def store_database_binding(
        self,
        execution: DatabaseCreationExecution,
        *,
        database_id: str,
        evidence_refs: Sequence[str],
    ) -> None:
        if execution.target is None:
            raise ValueError("Cannot bind database without a target.")
        target = execution.target
        binding = DatabaseArtifactBinding(
            {
                "schema_version": DatabaseArtifactBinding.SCHEMA_VERSION,
                "database_path": target.database_path,
                "database_id": database_id,
                "artifact_root_path": target.artifact_root_path,
                "corpus_path": target.corpus_path,
                "input_path": target.input_path,
                "documents_path": str(Path(target.artifact_root_path) / "Documents"),
                "error_cases_path": str(Path(target.artifact_root_path) / "Error Cases"),
                "semantic_release_path": target.semantic_release_path,
                "binding_provenance": {
                    "workflow_run_id": execution.workflow_run_id,
                    "created_by": "phase9.database_creation",
                },
                "created_at": utc_iso(),
                "updated_at": utc_iso(),
            }
        )
        self.bindings.put_verified_binding(binding, evidence_refs=evidence_refs)

    def put_attach_state(
        self,
        execution: DatabaseCreationExecution,
        *,
        release_path: str,
        release_id: str,
        release_version: str,
        release_fingerprint: str,
        runtime_locale: str,
        attach_receipt_id: str,
    ) -> None:
        if execution.target is None:
            raise ValueError("Cannot attach release without a target.")
        attach_state = SemanticReleaseAttachState(
            {
                "schema_version": SemanticReleaseAttachState.SCHEMA_VERSION,
                "release_path": release_path,
                "release_id": release_id,
                "release_version": release_version,
                "release_fingerprint": release_fingerprint,
                "runtime_locale": runtime_locale,
                "target_database_path": execution.target.database_path,
                "attach_receipt_id": attach_receipt_id,
                "attached_at": utc_iso(),
                "pointer_owner": AttachPointerOwner.KERNEL_HELD.value,
            }
        )
        self.attach_states.put_attach_state(attach_state)
