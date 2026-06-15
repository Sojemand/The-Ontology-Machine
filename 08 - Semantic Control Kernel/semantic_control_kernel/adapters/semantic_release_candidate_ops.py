from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import READ_ONLY_TIMEOUT_SECONDS, SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.adapters.semantic_release_refs import (
    artifact_root_from_semantic_release_folder,
    projection_refs_from_payload,
    taxonomy_ref_from_payload,
)
from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


class SemanticReleaseCandidateMixin:
    def create_custom_semantic_release(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        taxonomy_ref = taxonomy_ref_from_payload(payload)
        projection_refs = projection_refs_from_payload(payload)
        if not taxonomy_ref or not projection_refs:
            return self.blocked_by_kernel_precondition(
                kernel_function="create_custom_semantic_release",
                capability_status="implemented_in_pipeline",
                summary="Custom semantic release creation requires staged taxonomy and projection identities.",
                missing_fields=("taxonomy_ref", "projection_refs"),
            )
        semantic_release_folder = str(payload.get("semantic_release_folder") or payload.get("target_semantic_release_folder") or ".")
        artifact_root_path = artifact_root_from_semantic_release_folder(semantic_release_folder)
        target_identity = self.target_identity(payload, artifact_root_path=artifact_root_path)
        owner_request = self.phase19_request(
            owner_action="compile_semantic_release_candidate",
            request_payload=payload,
            target_identity=target_identity,
            taxonomy_ref=taxonomy_ref,
            projection_refs=projection_refs,
            runtime_locale=control_locale_or_default(payload.get("runtime_locale"), taxonomy_ref.get("runtime_locale")),
            semantic_release_folder=semantic_release_folder,
            release_identity_policy=dict(payload.get("release_identity_policy") or {}),
        )
        return self.invoke(
            kernel_function="create_custom_semantic_release",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action="compile_semantic_release_candidate",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("release_fingerprint",),
            target_identity=target_identity,
        )

    def validate_projection_binding(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        taxonomy_ref = dict(payload.get("taxonomy_ref") or {})
        projection_refs = projection_refs_from_payload(payload)
        if not taxonomy_ref:
            return self.blocked_by_kernel_precondition(
                kernel_function="validate_projections_against_taxonomy",
                capability_status="implemented_in_pipeline",
                summary="Projection validation requires a taxonomy reference.",
                missing_fields=("taxonomy_ref",),
            )
        target_identity = self.target_identity(payload, release_ref=dict(payload.get("release_ref") or {}))
        owner_request = self.phase19_request(
            owner_action="validate_projection_binding",
            request_payload=payload,
            target_identity=target_identity,
            taxonomy_ref=taxonomy_ref,
            projection_refs=projection_refs,
            release_ref=dict(payload.get("release_ref") or {}),
        )
        return self.invoke(
            kernel_function="validate_projections_against_taxonomy",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action="validate_projection_binding",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
            target_identity=target_identity,
        )

    def validate_projections_against_taxonomy(self, request_payload: Mapping[str, Any] | None = None) -> MissingCapabilityBlocker:
        return self.validate_projection_binding(request_payload)

    def remove_taxonomy_or_projection(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        component_kind = (request_payload or {}).get("component_kind") if isinstance(request_payload, Mapping) else None
        kernel_function = "remove_projection_from_database"
        payload = dict(request_payload or {})
        if component_kind != "projection":
            return self.blocked_by_kernel_precondition(
                kernel_function=kernel_function,
                capability_status="kernel_creation_internal_only",
                summary="Only the frozen default-taxonomy creation route may strip default projections from a staged release.",
                missing_fields=("component_kind=projection",),
            )
        release_ref = dict(payload.get("release_ref") or {})
        if not release_ref:
            return self.blocked_by_kernel_precondition(
                kernel_function=kernel_function,
                capability_status="implemented_in_pipeline",
                summary="Semantic release removal requires a release reference.",
                missing_fields=("release_ref",),
            )
        semantic_release_folder = str(payload.get("semantic_release_folder") or payload.get("semantic_release_path") or "")
        artifact_root_path = artifact_root_from_semantic_release_folder(semantic_release_folder)
        target_identity = self.target_identity(payload, artifact_root_path=artifact_root_path, release_ref=release_ref)
        owner_request = self.phase19_request(
            owner_action="remove_projection_from_release",
            request_payload=payload,
            target_identity=target_identity,
            release_ref=release_ref,
            projection_ids=[dict(payload.get("projection_ref") or {}).get("projection_id")] if isinstance(payload.get("projection_ref"), Mapping) else list(payload.get("projection_ids", [])),
            confirmation_receipt_ref=dict(payload.get("confirmation_receipt_ref") or {}),
        )
        return self.invoke(
            kernel_function=kernel_function,
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action="remove_projection_from_release",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("release_fingerprint",),
            target_identity=target_identity,
        )

    def merge_semantic_release_candidates(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        source_releases = [dict(item) for item in payload.get("source_releases", payload.get("source_release_refs", [])) if isinstance(item, Mapping)]
        if not source_releases:
            return self.blocked_by_kernel_precondition(
                kernel_function="merge_taxonomy_and_projections_additive",
                capability_status="implemented_in_pipeline",
                summary="Semantic release merge requires at least one source release reference.",
                missing_fields=("source_release_refs",),
            )
        target_identity = self.target_identity(payload, merge_run_id=str(payload.get("merge_run_id") or ""))
        owner_request = self.phase19_request(
            owner_action="merge_semantic_release_candidates",
            request_payload=payload,
            target_identity=target_identity,
            merge_run_id=str(payload.get("merge_run_id") or ""),
            source_release_refs=source_releases,
            collision_manifest_ref=dict(payload.get("collision_manifest_ref") or {}),
            selected_resolution_ref=dict(payload.get("selected_resolution_ref") or {}),
            projection_merge_mode=str(payload.get("projection_merge_mode") or ""),
            target_semantic_release_folder=str(payload.get("target_semantic_release_folder") or "."),
            runtime_locale=control_locale_or_default(payload.get("runtime_locale")),
        )
        return self.invoke(
            kernel_function="merge_taxonomy_and_projections_additive",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action="merge_semantic_release_candidates",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("merge_run_id", "release_fingerprint"),
            target_identity=target_identity,
        )
