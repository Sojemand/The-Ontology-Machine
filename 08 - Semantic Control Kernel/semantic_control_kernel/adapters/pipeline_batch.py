from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


class PipelineBatchAdapter(BasePipelineAdapter):
    adapter_name = "PipelineBatchAdapter"

    def create_batch_manifest(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        missing_fields = self._missing_fields(payload, ("workflow_run_id", "pipeline_batch_id", "artifact_root", "active_database", "semantic_release", "input_files"))
        if missing_fields:
            return self._missing_payload("pipeline_run", missing_fields, "pipeline_run requires batch identity, artifact root, active database, semantic release and input evidence.")
        active_database = dict(payload.get("active_database") or {})
        semantic_release = dict(payload.get("semantic_release") or {})
        target_identity = self.target_identity(
            payload,
            database_path=str(active_database.get("database_path") or ""),
            artifact_root_path=str(payload.get("artifact_root") or ""),
            pipeline_batch_id=str(payload.get("pipeline_batch_id") or ""),
            release_ref=semantic_release,
        )
        owner_request = self.phase19_request(
            owner_action="create_pipeline_batch_manifest",
            request_payload=payload,
            target_identity=target_identity,
            pipeline_batch_id=str(payload.get("pipeline_batch_id")),
            batch_kind=str(payload.get("batch_kind") or "manual_ingest"),
            active_database=active_database,
            artifact_root=str(payload.get("artifact_root") or ""),
            semantic_release=semantic_release,
            active_projections=list(payload.get("active_projections", [])),
            input_files=list(payload.get("input_files", [])),
            pending_manifest=dict(payload.get("pending_manifest") or {}),
        )
        return self.invoke(
            kernel_function="pipeline_run",
            owner_module="00 - Orchestrator",
            owner_contract_module="orchestrator.orchestrator_contract",
            owner_action="create_pipeline_batch_manifest",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("artifact_root_path_hash", "database_path_hash", "pipeline_batch_id", "release_fingerprint"),
            target_identity=target_identity,
            workflow_run_id=str(payload.get("workflow_run_id") or ""),
        )

    def finalize_batch_manifest(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        missing_fields = self._missing_fields(payload, ("workflow_run_id", "pipeline_batch_id", "artifact_root", "pending_manifest_ref", "materialized_records", "record_counts", "correlation_report"))
        if missing_fields:
            return self._missing_payload("pipeline_run", missing_fields, "pipeline_run finalize requires pending manifest, owner outputs and correlation evidence.")
        target_identity = self.target_identity(
            payload,
            artifact_root_path=str(payload.get("artifact_root") or ""),
            pipeline_batch_id=str(payload.get("pipeline_batch_id") or ""),
            extra={"artifact_root_path": str(payload.get("artifact_root") or "")},
        )
        owner_request = self.phase19_request(
            owner_action="finalize_pipeline_batch_manifest",
            request_payload=payload,
            target_identity=target_identity,
            pipeline_batch_id=str(payload.get("pipeline_batch_id")),
            pending_manifest_ref=dict(payload.get("pending_manifest_ref") or {}),
            orchestrator_run_ref=dict(payload.get("orchestrator_run_ref") or {}),
            corpus_load_refs=list(payload.get("corpus_load_refs", [])),
            output_artifacts=dict(payload.get("output_artifacts") or {}),
            materialized_records=list(payload.get("materialized_records", [])),
            record_counts=dict(payload.get("record_counts") or {}),
            correlation_report=dict(payload.get("correlation_report") or {}),
            final_manifest=dict(payload.get("final_manifest") or {}),
        )
        return self.invoke(
            kernel_function="pipeline_run",
            owner_module="00 - Orchestrator",
            owner_contract_module="orchestrator.orchestrator_contract",
            owner_action="finalize_pipeline_batch_manifest",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("artifact_root_path_hash", "pipeline_batch_id"),
            target_identity=target_identity,
            workflow_run_id=str(payload.get("workflow_run_id") or ""),
        )

    def _missing_payload(
        self,
        kernel_function: str,
        missing_fields: tuple[str, ...] | list[str],
        summary: str,
    ) -> AdapterCallResult:
        return self.blocked_by_kernel_precondition(
            kernel_function=kernel_function,
            capability_status="implemented_in_pipeline",
            summary=summary,
            missing_fields=missing_fields,
        )

    @staticmethod
    def _missing_fields(payload: Mapping[str, Any], required_fields: tuple[str, ...]) -> list[str]:
        return [field for field in required_fields if payload.get(field) in (None, "", [], {})]
