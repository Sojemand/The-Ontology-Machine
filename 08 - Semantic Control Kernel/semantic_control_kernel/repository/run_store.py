from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository._helpers import payload_from_mapping, target_identity_index_key
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import WorkflowRunRecord
from semantic_control_kernel.repository.terminal_transition import move_active_to_history
from semantic_control_kernel.repository.trace_store import TraceLinkStore


def _validate_workflow_run(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Workflow run record must be an object.")
    WorkflowRunRecord.from_dict(payload)


class WorkflowRunStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "workflow_runs")
        self._trace_store = TraceLinkStore(paths)

    def create_run(self, workflow_tool, target_identity, started_by, *, workflow_run_id: str | None = None) -> WorkflowRunRecord:
        now = utc_iso()
        record = WorkflowRunRecord(
            {
                "created_at": now,
                "schema_version": WorkflowRunRecord.SCHEMA_VERSION,
                "started_by": started_by,
                "status": "running",
                "target_identity": payload_from_mapping(target_identity),
                "updated_at": now,
                "workflow_run_id": workflow_run_id or generate_id("workflow_run_id"),
                "workflow_tool": workflow_tool,
            }
        )
        path = self._active_path(record.workflow_run_id)
        self._json.write_json(path, record.to_dict(), immutable=True, validator=_validate_workflow_run)
        self._trace_store.create_trace_context(
            workflow_run_id=record.workflow_run_id,
            workflow_tool=record.workflow_tool,
            started_by=record.started_by,
            root_target_identity_ref=f"workflow_runs/active/{record.workflow_run_id}.json#target_identity",
            state_root_ref="state",
        )
        self._trace_store.append_link(
            workflow_run_id=record.workflow_run_id,
            object_kind="workflow_run",
            object_id=record.workflow_run_id,
            object_ref=self.paths.relative_to_state_root(path),
        )
        return record

    def get_run(self, workflow_run_id) -> WorkflowRunRecord:
        for path in (self._active_path(workflow_run_id), self._history_path(workflow_run_id)):
            if path.exists():
                return WorkflowRunRecord.from_dict(self._json.read_json(path, validator=_validate_workflow_run))
        raise ResumeStateNotFoundError(f"Workflow run not found: {workflow_run_id}")

    def list_active_runs(self, target_identity=None) -> list[WorkflowRunRecord]:
        expected_key = target_identity_index_key(target_identity) if target_identity is not None else None
        records = []
        for path in sorted(self.paths.workflow_runs_active_dir.glob("*.json")):
            record = WorkflowRunRecord.from_dict(self._json.read_json(path, validator=_validate_workflow_run))
            if record.status not in {"running", "waiting"}:
                continue
            if expected_key is None or target_identity_index_key(record.target_identity) == expected_key:
                records.append(record)
        return records

    def mark_run_waiting(self, workflow_run_id, resume_state_ref) -> WorkflowRunRecord:
        return self._update_active(workflow_run_id, status="waiting", resume_state_ref=resume_state_ref)

    def mark_run_running(self, workflow_run_id, *, target_identity=None, resume_state_ref=None) -> WorkflowRunRecord:
        updates = {"status": "running"}
        if target_identity is not None:
            updates["target_identity"] = payload_from_mapping(target_identity)
        if resume_state_ref is not None:
            updates["resume_state_ref"] = resume_state_ref
        return self._update_active(workflow_run_id, **updates)

    def mark_run_completed(self, workflow_run_id, operation_receipt_id) -> WorkflowRunRecord:
        record = self._update_active(workflow_run_id, status="completed", operation_receipt_id=operation_receipt_id)
        self._move_to_history(record)
        return record

    def mark_run_failed(self, workflow_run_id, support_bundle_ref=None) -> WorkflowRunRecord:
        updates = {"support_bundle_ref": support_bundle_ref} if support_bundle_ref is not None else {}
        record = self._update_active(workflow_run_id, status="failed", **updates)
        self._move_to_history(record)
        return record

    def mark_run_cancelled(self, workflow_run_id, recovery_receipt_id=None) -> WorkflowRunRecord:
        updates = {"recovery_receipt_id": recovery_receipt_id} if recovery_receipt_id is not None else {}
        record = self._update_active(workflow_run_id, status="cancelled", **updates)
        self._move_to_history(record)
        return record

    def _update_active(self, workflow_run_id: str, **updates) -> WorkflowRunRecord:
        path = self._active_path(workflow_run_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Active workflow run not found: {workflow_run_id}")
        payload = self._json.read_json(path, validator=_validate_workflow_run)
        payload.update(updates)
        payload["updated_at"] = utc_iso()
        record = WorkflowRunRecord.from_dict(payload)
        self._json.write_json(path, record.to_dict(), validator=_validate_workflow_run)
        return record

    def _move_to_history(self, record: WorkflowRunRecord) -> None:
        active = self._active_path(record.workflow_run_id)
        history = self._history_path(record.workflow_run_id)
        move_active_to_history(
            self._json,
            active_path=active,
            history_path=history,
            payload=record.to_dict(),
            validator=_validate_workflow_run,
            duplicate_message=f"Workflow history already exists: {record.workflow_run_id}",
        )
        KernelStateHardCapService(self.paths).prune_workflow_run_history()

    def _active_path(self, workflow_run_id: str) -> Path:
        return self.paths.workflow_runs_active_dir / f"{require_state_id('workflow_run_id', workflow_run_id)}.json"

    def _history_path(self, workflow_run_id: str) -> Path:
        return self.paths.workflow_runs_history_dir / f"{require_state_id('workflow_run_id', workflow_run_id)}.json"
