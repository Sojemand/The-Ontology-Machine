from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.batch_policy import (
    canonical_manifest_fingerprint,
    is_valid_pipeline_batch_id,
)
from semantic_control_kernel.validation.contract_validation import KernelContractError, validate_contract


class BatchValidationError(KernelContractError):
    pass


class ManifestFingerprintError(BatchValidationError):
    pass


class MaterializationRefError(BatchValidationError):
    pass


def validate_pipeline_batch_manifest(payload: Mapping[str, Any]) -> None:
    validate_contract(payload, expected_schema_version="kernel.pipeline_batch_manifest.v1")
    batch_id = str(payload.get("pipeline_batch_id", ""))
    if not is_valid_pipeline_batch_id(batch_id):
        raise BatchValidationError("pipeline_batch_id does not match the Phase 11 pbt timestamp shape.")
    expected = canonical_manifest_fingerprint(payload)
    actual = payload.get("manifest_fingerprint")
    if actual != expected:
        raise ManifestFingerprintError("manifest_fingerprint does not match canonical manifest payload.")
    owner_run_refs = payload.get("owner_run_refs")
    _require_mapping_fields(
        owner_run_refs,
        required=("orchestrator_run_id", "orchestrator_receipt_ref"),
        error_message="owner_run_refs must include orchestrator_run_id and orchestrator_receipt_ref.",
    )
    _validate_materialization_refs(payload)


def _require_mapping_fields(
    value: Any,
    *,
    required: tuple[str, ...],
    error_message: str,
) -> None:
    if not isinstance(value, Mapping) or any(value.get(field) in (None, "", [], {}) for field in required):
        raise BatchValidationError(error_message)


def _validate_materialization_refs(payload: Mapping[str, Any]) -> None:
    release = payload["semantic_release"]
    projections = payload["active_projections"]
    first_projection = projections[0] if projections else {}
    for record in payload.get("materialized_records", []):
        if not isinstance(record, Mapping):
            raise MaterializationRefError("materialized_records entries must be objects.")
        ref = record.get("record_semantic_materialization_ref")
        if not isinstance(ref, Mapping):
            raise MaterializationRefError("record_semantic_materialization_ref must resolve to an object.")
        expected = {
            "schema_version": "kernel.record_semantic_materialization_ref.v1",
            "pipeline_batch_id": payload["pipeline_batch_id"],
            "document_id": record.get("document_id"),
            "record_id": record.get("record_id"),
            "semantic_release_id": release.get("semantic_release_id"),
            "semantic_release_version": release.get("semantic_release_version"),
            "release_fingerprint": release.get("release_fingerprint"),
            "taxonomy_fingerprint": release.get("taxonomy_fingerprint"),
            "projection_id": ref.get("projection_id") or first_projection.get("projection_id"),
            "projection_fingerprint": ref.get("projection_fingerprint") or first_projection.get("projection_fingerprint"),
        }
        for field, expected_value in expected.items():
            if ref.get(field) != expected_value:
                raise MaterializationRefError(
                    f"record_semantic_materialization_ref.{field} must match manifest materialization identity."
                )
