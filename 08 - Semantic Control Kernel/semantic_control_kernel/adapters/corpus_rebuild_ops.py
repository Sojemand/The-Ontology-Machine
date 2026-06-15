from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import LONG_RUNNING_TIMEOUT_SECONDS, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


class CorpusRebuildOpsMixin:
    def rebuild_from_artifacts(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        action = "create_and_rebuild_new_corpus_db" if payload.get("create_new") else "rebuild_from_artifacts"
        artifact_root = str(payload.get("pipeline_root") or payload.get("artifact_root") or "").strip()
        corpus_db_path = _target_database_path(payload)
        owner_request = _rebuild_owner_request(action, payload, artifact_root, corpus_db_path)
        target_identity = self.target_identity(
            payload,
            database_path=corpus_db_path or None,
            artifact_root_path=artifact_root or None,
        )
        return self.invoke(
            kernel_function="run_corpus_builder",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action=action,
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path|database_path_hash", "artifact_root_path|artifact_root_path_hash"),
            target_identity=target_identity,
        )

    def basic_relation_mining(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        database_path = str(payload.get("database_path") or payload.get("corpus_db_path") or "").strip()
        if not database_path:
            return self.blocked_by_kernel_precondition(
                kernel_function="basic_relation_mining",
                capability_status="implemented_in_pipeline",
                summary="Basic relation mining requires a resolved Corpus database path.",
                missing_fields=("database_path",),
            )
        return self.invoke(
            kernel_function="basic_relation_mining",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="basic_relation_mining",
            request_payload={
                "action": "basic_relation_mining",
                "corpus_db_path": database_path,
                "dry_run": bool(payload.get("dry_run", False)),
            },
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=not bool(payload.get("dry_run", False)),
            required_target_proof_fields=("database_path|database_path_hash",),
            target_identity=self.target_identity(payload, database_path=database_path),
        )

    def backfill_sql(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
        merge_run_id = str(payload.get("merge_run_id") or selection.get("merge_run_id") or "")
        if not merge_run_id:
            return self.blocked_by_kernel_precondition(
                kernel_function="backfill_sql",
                capability_status="implemented_in_pipeline",
                summary="Merge backfill requires the active merge run identity.",
                missing_fields=("merge_run_id",),
            )
        target_database_path = str(payload.get("target_database_path") or selection.get("target_database_path") or "")
        target_database_path_hash = self.owner_path_hash(target_database_path) if target_database_path else ""
        target_identity = self.target_identity(
            payload,
            database_path=target_database_path or None,
            merge_run_id=merge_run_id,
            extra={"target_database_path_hash": target_database_path_hash} if target_database_path_hash else None,
        )
        owner_request = self.phase19_request(
            owner_action="backfill_sql_from_merge_artifacts",
            request_payload=payload,
            target_identity=target_identity,
            merge_run_id=merge_run_id,
            target_database_path=target_database_path,
            artifact_root=str(payload.get("artifact_root") or selection.get("target_artifact_root") or ""),
            id_map=dict(payload.get("id_map") or {}),
            backfill_scope=str(payload.get("backfill_scope") or "all"),
        )
        return self.invoke(
            kernel_function="backfill_sql",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="backfill_sql_from_merge_artifacts",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path_hash", "merge_run_id"),
            target_identity=target_identity,
        )


def _target_database_path(payload: Mapping[str, Any]) -> str:
    target_identity = payload.get("target_identity") if isinstance(payload.get("target_identity"), Mapping) else {}
    return str(
        payload.get("corpus_db_path")
        or payload.get("target_database_path")
        or target_identity.get("target_database_path")
        or ""
    ).strip()


def _rebuild_owner_request(action: str, payload: Mapping[str, Any], artifact_root: str, corpus_db_path: str) -> dict[str, Any]:
    owner_request: dict[str, Any] = {"action": action, "pipeline_root": artifact_root}
    if action == "rebuild_from_artifacts":
        owner_request["corpus_db_path"] = corpus_db_path
        owner_request["replace_existing"] = bool(payload.get("replace_existing", True))
    release_path = str(
        payload.get("release_path")
        or (payload.get("loaded_semantic_release", {}) if isinstance(payload.get("loaded_semantic_release"), Mapping) else {}).get("loaded_release_path")
        or ""
    ).strip()
    if release_path:
        owner_request["release_path"] = release_path
    optional_keys = ["normalized_dir", "structured_dir", "validation_dir", "raw_dir"]
    if action == "create_and_rebuild_new_corpus_db":
        optional_keys.append("confirmation_artifact_path")
    for key in optional_keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            owner_request[key] = value
    return {key: value for key, value in owner_request.items() if value not in ("", None, [], {})}
