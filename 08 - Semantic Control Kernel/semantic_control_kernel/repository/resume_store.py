from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository._helpers import contract_payload, target_identity_index_key
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import DuplicateStateObjectError, ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.state import WorkflowResumeState
from semantic_control_kernel.validation.contract_validation import validate_contract


def _validate_resume(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Workflow resume state must be an object.")
    validate_contract(payload, expected_schema_version=WorkflowResumeState.SCHEMA_VERSION)


class WorkflowResumeStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "resume")

    def put_resume_state(self, resume_state: WorkflowResumeState) -> None:
        payload = contract_payload(resume_state, WorkflowResumeState)
        path = self._resume_path(payload["workflow_run_id"])
        if path.exists():
            raise DuplicateStateObjectError(f"Resume state already exists: {payload['workflow_run_id']}")
        self._json.write_json(path, payload, immutable=True, validator=_validate_resume)

    def get_resume_state(self, workflow_run_id) -> WorkflowResumeState:
        path = self._resume_path(workflow_run_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Resume state not found: {workflow_run_id}")
        return WorkflowResumeState.from_dict(self._json.read_json(path, validator=_validate_resume))

    def list_resumable(self, target_identity=None) -> list[WorkflowResumeState]:
        expected_key = target_identity_index_key(target_identity) if target_identity is not None else None
        states = []
        for path in sorted(self.paths.resume_dir.glob("*.resume.json")):
            state = WorkflowResumeState.from_dict(self._json.read_json(path, validator=_validate_resume))
            selected_targets = state.payload.get("selected_targets")
            if expected_key is None:
                states.append(state)
            elif isinstance(selected_targets, list) and any(
                isinstance(item, dict) and target_identity_index_key(item) == expected_key for item in selected_targets
            ):
                states.append(state)
        return states

    def mark_resume_consumed(self, workflow_run_id, operation_receipt_id) -> None:
        self._json.delete_json(self._resume_path(workflow_run_id))

    def mark_resume_expired(self, workflow_run_id, reason) -> None:
        self._json.delete_json(self._resume_path(workflow_run_id))

    def _resume_path(self, workflow_run_id: str) -> Path:
        return self.paths.resume_dir / f"{require_state_id('workflow_run_id', workflow_run_id)}.resume.json"
