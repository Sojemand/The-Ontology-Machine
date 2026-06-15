from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository._helpers import contract_payload, parse_contract_payload
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.attach_state_store import ActiveArtifactTreeRefStore
from semantic_control_kernel.repository.errors import BindingConflictError, BindingNotFoundError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import require_state_id, utc_compact_timestamp
from semantic_control_kernel.repository.paths import StatePaths, path_hash, stable_hash, utc_iso
from semantic_control_kernel.types.state import DatabaseArtifactBinding
from semantic_control_kernel.validation.contract_validation import validate_contract


def _validate_binding(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Database artifact binding must be an object.")
    validate_contract(payload, expected_schema_version=DatabaseArtifactBinding.SCHEMA_VERSION)


def _validate_index(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Binding index must be an object.")
    required = {"schema_version", "index_kind", "index_key", "binding_ref", "updated_at"}
    missing = required - set(payload)
    if missing:
        raise BindingConflictError(f"Binding index missing field(s): {', '.join(sorted(missing))}")


class DatabaseArtifactBindingRegistry:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "bindings")
        self._artifact_refs = ActiveArtifactTreeRefStore(paths)

    def put_verified_binding(self, binding: DatabaseArtifactBinding, evidence_refs) -> None:
        payload = contract_payload(binding, DatabaseArtifactBinding)
        database_id_hash = self._database_id_hash(payload["database_id"])
        database_path_hash = path_hash(payload["database_path"])
        artifact_root_path_hash = path_hash(payload["artifact_root_path"])
        if not Path(payload["database_path"]).exists():
            raise BindingConflictError("Database binding requires an existing target database path.")
        if self._artifact_refs.get_by_artifact_root_hash(artifact_root_path_hash) is None:
            raise BindingConflictError("Database binding requires an active Artifact Tree ref.")
        self._reject_conflicts(payload, database_id_hash, database_path_hash, artifact_root_path_hash)
        record_path = self._record_path(database_id_hash)
        record_payload = {**payload, "binding_provenance": {**payload["binding_provenance"], "evidence_refs": list(evidence_refs)}}
        self._json.write_json(record_path, record_payload, immutable=True, validator=_validate_binding)
        self._write_index(
            self.paths.bindings_index_by_database_path_dir / f"{database_path_hash}.json",
            "by_database_path",
            database_path_hash,
            record_path,
        )
        self._write_index(
            self.paths.bindings_index_by_artifact_root_dir / f"{artifact_root_path_hash}.json",
            "by_artifact_root",
            artifact_root_path_hash,
            record_path,
        )

    def get_by_database_id(self, database_id) -> DatabaseArtifactBinding:
        return self._read_binding(self._record_path(self._database_id_hash(database_id)))

    def get_by_database_path(self, database_path) -> DatabaseArtifactBinding:
        return self._read_from_index(self.paths.bindings_index_by_database_path_dir / f"{path_hash(database_path)}.json")

    def get_by_artifact_root(self, artifact_root_path) -> DatabaseArtifactBinding:
        return self._read_from_index(self.paths.bindings_index_by_artifact_root_dir / f"{path_hash(artifact_root_path)}.json")

    def list_bindings(self) -> list[DatabaseArtifactBinding]:
        return [self._read_binding(path) for path in sorted(self.paths.bindings_records_dir.glob("*.json"))]

    def mark_binding_stale(self, binding_ref, reason, recovery_receipt_id=None) -> None:
        binding = self._resolve_binding_ref(binding_ref)
        payload = binding.to_dict()
        database_id_hash = self._database_id_hash(payload["database_id"])
        database_path_hash = path_hash(payload["database_path"])
        artifact_root_path_hash = path_hash(payload["artifact_root_path"])
        history_dir = self.paths.bindings_history_dir / database_id_hash
        event = recovery_receipt_id or "stale"
        history_payload = {
            "binding": payload,
            "database_id_hash": database_id_hash,
            "database_path_hash": database_path_hash,
            "artifact_root_path_hash": artifact_root_path_hash,
            "reason": reason,
            "recovery_receipt_id": recovery_receipt_id,
            "schema_version": "repository.database_artifact_binding_history.v1",
            "staled_at": utc_iso(),
        }
        self._json.write_json(history_dir / f"{utc_compact_timestamp()}_{require_state_id('recovery_receipt_id', event)}.json", history_payload, immutable=True)
        for path in (
            self._record_path(database_id_hash),
            self.paths.bindings_index_by_database_path_dir / f"{database_path_hash}.json",
            self.paths.bindings_index_by_artifact_root_dir / f"{artifact_root_path_hash}.json",
        ):
            self._json.delete_json(path)
        KernelStateHardCapService(self.paths).prune_nested_history_root(self.paths.bindings_history_dir)

    def _reject_conflicts(self, payload: Mapping[str, Any], database_id_hash: str, database_path_hash: str, artifact_root_path_hash: str) -> None:
        checks = [
            self._record_path(database_id_hash),
            self.paths.bindings_index_by_database_path_dir / f"{database_path_hash}.json",
            self.paths.bindings_index_by_artifact_root_dir / f"{artifact_root_path_hash}.json",
        ]
        for path in checks:
            if path.exists():
                raise BindingConflictError("Active database/artifact binding already exists for this evidence.")
        for existing in self.list_bindings():
            if (
                existing.payload["database_path"] == payload["database_path"]
                or existing.payload["database_id"] == payload["database_id"]
                or existing.payload["artifact_root_path"] == payload["artifact_root_path"]
            ):
                raise BindingConflictError("Conflicting database/artifact binding evidence.")

    def _read_from_index(self, index_path: Path) -> DatabaseArtifactBinding:
        if not index_path.exists():
            raise BindingNotFoundError(f"Binding index not found: {index_path.name}")
        index = self._json.read_json(index_path, validator=_validate_index)
        return self._read_binding(self.paths.safe_path(index["binding_ref"]["state_path"]))

    def _read_binding(self, path: Path) -> DatabaseArtifactBinding:
        if not path.exists():
            raise BindingNotFoundError(f"Binding not found: {path.name}")
        return parse_contract_payload(self._json.read_json(path, validator=_validate_binding), DatabaseArtifactBinding)

    def _resolve_binding_ref(self, binding_ref) -> DatabaseArtifactBinding:
        if isinstance(binding_ref, DatabaseArtifactBinding):
            return binding_ref
        if isinstance(binding_ref, Mapping):
            if "database_id" in binding_ref:
                return self.get_by_database_id(binding_ref["database_id"])
            if "database_path" in binding_ref:
                return self.get_by_database_path(binding_ref["database_path"])
            if "artifact_root_path" in binding_ref:
                return self.get_by_artifact_root(binding_ref["artifact_root_path"])
        return self.get_by_database_id(str(binding_ref))

    def _write_index(self, path: Path, index_kind: str, index_key: str, record_path: Path) -> None:
        payload = {
            "binding_ref": {"state_path": self.paths.relative_to_state_root(record_path)},
            "index_key": index_key,
            "index_kind": index_kind,
            "schema_version": "repository.database_artifact_binding_index.v1",
            "updated_at": utc_iso(),
        }
        self._json.write_json(path, payload, immutable=True, validator=_validate_index)

    def _record_path(self, database_id_hash: str) -> Path:
        return self.paths.bindings_records_dir / f"{database_id_hash}.json"

    def _database_id_hash(self, database_id: str) -> str:
        return stable_hash(str(database_id))
