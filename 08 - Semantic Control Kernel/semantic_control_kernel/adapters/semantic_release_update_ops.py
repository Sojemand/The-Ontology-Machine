from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.adapters.semantic_release_refs import artifact_root_from_semantic_release_folder
from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


class SemanticReleaseUpdateMixin:
    def stage_taxonomy(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        semantic_release_folder = str(payload.get("semantic_release_path") or payload.get("semantic_release_folder") or "")
        update_state = payload.get("update_state") or payload.get("custom_taxonomy")
        if not semantic_release_folder or not isinstance(update_state, Mapping):
            return self.blocked_by_kernel_precondition(
                kernel_function="stage_custom_taxonomy_for_semantic_release",
                capability_status="implemented_in_pipeline",
                summary="Taxonomy staging requires a semantic release folder and update-state payload.",
                missing_fields=("semantic_release_path", "update_state"),
            )
        artifact_root_path = artifact_root_from_semantic_release_folder(semantic_release_folder)
        target_identity = self.target_identity(payload, artifact_root_path=artifact_root_path)
        owner_request = self.phase19_request(
            owner_action="materialize_custom_taxonomy_artifact",
            request_payload=payload,
            target_identity=target_identity,
            update_state_payload=dict(update_state),
            semantic_release_folder=semantic_release_folder,
            runtime_locale=control_locale_or_default(dict(update_state).get("runtime_locale")),
        )
        return self._invoke_semantic_edit(
            "stage_custom_taxonomy_for_semantic_release",
            "materialize_custom_taxonomy_artifact",
            owner_request,
            target_identity,
            required_target_proof_fields=("artifact_root_path_hash", "taxonomy_fingerprint"),
        )

    def stage_projections(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        semantic_release_folder = str(payload.get("semantic_release_path") or payload.get("semantic_release_folder") or "")
        update_state = payload.get("update_state") or payload.get("custom_projection")
        taxonomy_ref = dict(payload.get("taxonomy_ref") or {})
        if not semantic_release_folder or not isinstance(update_state, Mapping):
            return self.blocked_by_kernel_precondition(
                kernel_function="stage_custom_projections_for_semantic_release",
                capability_status="implemented_in_pipeline",
                summary="Projection staging requires a semantic release folder and update-state payload.",
                missing_fields=("semantic_release_path", "update_state"),
            )
        artifact_root_path = artifact_root_from_semantic_release_folder(semantic_release_folder)
        target_identity = self.target_identity(payload, artifact_root_path=artifact_root_path)
        owner_request = self.phase19_request(
            owner_action="materialize_custom_projection_artifact",
            request_payload=payload,
            target_identity=target_identity,
            update_state_payload=dict(update_state),
            taxonomy_ref=taxonomy_ref,
            semantic_release_folder=semantic_release_folder,
            runtime_locale=control_locale_or_default(dict(update_state).get("runtime_locale"), taxonomy_ref.get("runtime_locale")),
        )
        return self._invoke_semantic_edit(
            "stage_custom_projections_for_semantic_release",
            "materialize_custom_projection_artifact",
            owner_request,
            target_identity,
            required_target_proof_fields=("artifact_root_path_hash", "projection_fingerprint"),
        )

    def _invoke_semantic_edit(self, kernel_function, owner_action, owner_request, target_identity, *, required_target_proof_fields):
        return self.invoke(
            kernel_function=kernel_function,
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action=owner_action,
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=required_target_proof_fields,
            target_identity=target_identity,
        )
