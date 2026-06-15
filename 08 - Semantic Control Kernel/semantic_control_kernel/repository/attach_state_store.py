from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository._helpers import contract_payload, parse_contract_payload, payload_from_mapping, target_identity_hash
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import DuplicateStateObjectError, ResumeStateNotFoundError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import require_state_id, utc_compact_timestamp
from semantic_control_kernel.repository.paths import StatePaths, path_hash
from semantic_control_kernel.repository.records import ActiveArtifactTreeRef
from semantic_control_kernel.types.state import SemanticReleaseAttachState
from semantic_control_kernel.validation.contract_validation import validate_contract


def _validate_attach_state(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Attach state must be an object.")
    validate_contract(payload, expected_schema_version=SemanticReleaseAttachState.SCHEMA_VERSION)


def _validate_artifact_tree_ref(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Active artifact tree ref must be an object.")
    ActiveArtifactTreeRef.from_dict(payload)


class AttachStateStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "attach_states")

    def put_attach_state(self, state: SemanticReleaseAttachState) -> None:
        payload = contract_payload(state, SemanticReleaseAttachState)
        target_hash = path_hash(payload["target_database_path"])
        self._json.write_json(self._active_path(target_hash), payload, validator=_validate_attach_state)

    def get_attach_state_for_database(self, target_identity) -> SemanticReleaseAttachState | None:
        target_hash = self._target_hash(target_identity)
        path = self._active_path(target_hash)
        if not path.exists():
            return None
        return parse_contract_payload(self._json.read_json(path, validator=_validate_attach_state), SemanticReleaseAttachState)

    def clear_attach_state(self, target_identity, operation_receipt_id) -> None:
        target_hash = self._target_hash(target_identity)
        path = self._active_path(target_hash)
        if not path.exists():
            return
        payload = self._json.read_json(path, validator=_validate_attach_state)
        history = self._history_path(target_hash, operation_receipt_id)
        self._json.write_json(history, payload, immutable=True, validator=_validate_attach_state)
        self._json.delete_json(path)
        KernelStateHardCapService(self.paths).prune_nested_history_root(self.paths.attach_states_history_dir)

    def supersede_attach_state(self, target_identity, replacement_state, operation_receipt_id) -> None:
        self.clear_attach_state(target_identity, operation_receipt_id)
        self.put_attach_state(replacement_state)

    def _target_hash(self, target_identity) -> str:
        payload = payload_from_mapping(target_identity)
        if "database_path_hash" in payload:
            return str(payload["database_path_hash"])
        if "database_path" in payload:
            return path_hash(payload["database_path"])
        if "target_hash" in payload:
            return str(payload["target_hash"])
        return target_identity_hash(payload)

    def _active_path(self, target_hash: str) -> Path:
        return self.paths.attach_states_by_database_dir / f"{target_hash}.json"

    def _history_path(self, target_hash: str, operation_receipt_id: str) -> Path:
        return self.paths.attach_states_history_dir / target_hash / f"{utc_compact_timestamp()}_{require_state_id('operation_receipt_id', operation_receipt_id)}.json"


class ActiveArtifactTreeRefStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "artifact_trees")

    def put_verified_artifact_tree_ref(self, ref: ActiveArtifactTreeRef | Mapping[str, Any], evidence_refs) -> None:
        payload = ref.to_dict() if isinstance(ref, ActiveArtifactTreeRef) else dict(ref)
        payload["evidence_refs"] = list(evidence_refs)
        payload["status"] = "active"
        record = ActiveArtifactTreeRef(payload)
        self._json.write_json(self._active_path(record.artifact_root_path_hash), record.to_dict(), validator=_validate_artifact_tree_ref)

    def get_by_artifact_root_hash(self, artifact_root_path_hash) -> ActiveArtifactTreeRef | None:
        path = self._active_path(artifact_root_path_hash)
        if not path.exists():
            return None
        return ActiveArtifactTreeRef.from_dict(self._json.read_json(path, validator=_validate_artifact_tree_ref))

    def mark_artifact_tree_ref_stale(self, artifact_root_path_hash, reason, operation_receipt_id=None) -> None:
        path = self._active_path(artifact_root_path_hash)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Active Artifact Tree ref not found: {artifact_root_path_hash}")
        record = ActiveArtifactTreeRef.from_dict(self._json.read_json(path, validator=_validate_artifact_tree_ref))
        stale = record.with_updates(status="stale", stale_reason=reason, operation_receipt_id=operation_receipt_id)
        event = operation_receipt_id or "stale"
        history = self.paths.artifact_trees_history_dir / artifact_root_path_hash / f"{utc_compact_timestamp()}_{require_state_id('operation_receipt_id', event)}.json"
        self._json.write_json(history, stale.to_dict(), immutable=True, validator=_validate_artifact_tree_ref)
        self._json.delete_json(path)
        KernelStateHardCapService(self.paths).prune_nested_history_root(self.paths.artifact_trees_history_dir)

    def _active_path(self, artifact_root_path_hash: str) -> Path:
        return self.paths.artifact_trees_active_dir / f"{artifact_root_path_hash}.json"
