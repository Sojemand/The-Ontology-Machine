from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.base import READ_ONLY_TIMEOUT_SECONDS, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.repository.atomic_json import atomic_write_json
from semantic_control_kernel.repository.paths import stable_hash, utc_iso
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class CorpusDatabaseOpsMixin:
    def create_empty_database(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        database_path = str(payload.get("database_path") or payload.get("corpus_db_path") or "")
        if not database_path:
            return self.blocked_by_kernel_precondition(
                kernel_function="create_empty_database",
                capability_status="implemented_in_pipeline",
                summary="Empty database creation requires a resolved database path.",
                missing_fields=("database_path",),
            )
        return self.invoke(
            kernel_function="create_empty_database",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="create_empty_corpus_db",
            request_payload={"action": "create_empty_corpus_db", "corpus_db_path": database_path, "activate_context": False},
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path|database_path_hash",),
            target_identity=payload.get("target_identity") if isinstance(payload.get("target_identity"), Mapping) else None,
        )

    def reset_database(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        database_path = str(payload.get("database_path") or payload.get("corpus_db_path") or "")
        if not database_path:
            return self.blocked_by_kernel_precondition(
                kernel_function="reset_database",
                capability_status="kernel_composition_over_existing_primitives",
                summary="Database reset requires a resolved Corpus database path.",
                missing_fields=("database_path",),
            )
        confirmation_path = self._resolve_reset_confirmation_path(payload, database_path)
        if isinstance(confirmation_path, AdapterCallResult):
            return confirmation_path
        return self.invoke(
            kernel_function="reset_database",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="reset_active_corpus_db",
            request_payload={
                "action": "reset_active_corpus_db",
                "corpus_db_path": database_path,
                "confirmation_artifact_path": confirmation_path,
            },
            capability_status="kernel_composition_over_existing_primitives",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path|database_path_hash",),
            target_identity=self.target_identity(payload, database_path=database_path),
        )

    def _resolve_reset_confirmation_path(self, payload: Mapping[str, Any], database_path: str) -> str | AdapterCallResult:
        confirmation_artifact_path = str(payload.get("confirmation_artifact_path") or "").strip()
        if confirmation_artifact_path:
            return confirmation_artifact_path
        confirmation = payload.get("confirmation")
        if not isinstance(confirmation, Mapping):
            return self.blocked_by_kernel_precondition(
                kernel_function="reset_database",
                capability_status="kernel_composition_over_existing_primitives",
                summary="Database reset requires a target-bound confirmation receipt.",
                missing_fields=("confirmation",),
            )
        return str(self._write_reset_confirmation_artifact(database_path=database_path, confirmation=confirmation))

    def _write_reset_confirmation_artifact(self, *, database_path: str, confirmation: Mapping[str, Any]) -> Path:
        self.paths.ensure_layout()
        confirmation_id = str(
            confirmation.get("confirmation_receipt_id")
            or confirmation.get("confirmation_request_id")
            or stable_hash(f"reset_database:{database_path}:{repr(sorted(confirmation.items()))}")
        )
        artifact_path = self.paths.tmp_dir / "reset_confirmations" / f"{confirmation_id}.json"
        atomic_write_json(
            artifact_path,
            {
                "artifact_version": "reset_active_corpus_db_confirmation_v1",
                "confirmed": True,
                "corpus_db_path": str(Path(database_path).resolve(strict=False)),
                "created_at": utc_iso(),
                "kernel_confirmation_ref": dict(confirmation),
                "reason": "Kernel reset_database confirmation receipt.",
                "requested_action": "reset_active_corpus_db",
            },
        )
        return artifact_path

    def read_semantic_status(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        payload.setdefault("action", "semantic_status")
        return self.invoke(
            kernel_function="read_semantic_status",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="semantic_status",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
        )

    def read_active_semantic_release(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        payload.setdefault("action", "read_active_semantic_release")
        return self.invoke(
            kernel_function="read_active_semantic_release",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="read_active_semantic_release",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
        )

    def load_document(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        return self.invoke(
            kernel_function="load_document",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="load_document",
            request_payload=request_payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path|database_path_hash",),
        )
