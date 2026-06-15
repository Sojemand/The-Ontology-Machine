from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.adapters.semantic_release_refs import projection_refs_from_update_state


class SemanticReleaseComponentMixin:
    def create_custom_taxonomy(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        update_state = payload.get("update_state")
        if not isinstance(update_state, Mapping):
            return self.blocked_by_kernel_precondition(
                kernel_function="create_custom_taxonomy",
                capability_status="implemented_in_pipeline",
                summary="Custom taxonomy creation requires a taxonomy update-state payload.",
                missing_fields=("update_state",),
            )
        fingerprint = stable_hash(repr(sorted(dict(update_state).items())))
        output = {
            "taxonomy_id": str(update_state.get("taxonomy_id") or f"taxonomy_{fingerprint[:12]}"),
            "taxonomy_fingerprint": fingerprint,
            "component_identity": {
                "taxonomy_id": str(update_state.get("taxonomy_id") or f"taxonomy_{fingerprint[:12]}"),
                "taxonomy_fingerprint": fingerprint,
                "runtime_locale": control_locale_or_default(update_state.get("runtime_locale")),
            },
        }
        return self.ok_result(
            kernel_function="create_custom_taxonomy",
            capability_status="implemented_in_pipeline",
            output_refs=output,
        )

    def create_custom_projection(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        update_state = payload.get("update_state")
        if not isinstance(update_state, Mapping):
            return self.blocked_by_kernel_precondition(
                kernel_function="create_custom_projection",
                capability_status="implemented_in_pipeline",
                summary="Custom projection creation requires a projection update-state payload.",
                missing_fields=("update_state",),
            )
        projection_refs = projection_refs_from_update_state(update_state)
        if not projection_refs:
            return self.blocked_by_kernel_precondition(
                kernel_function="create_custom_projection",
                capability_status="implemented_in_pipeline",
                summary="Custom projection creation requires projection_precursors with projection_id.",
                missing_fields=("projection_precursors[].projection_id",),
            )
        projection_ids = [item["projection_id"] for item in projection_refs]
        fingerprints = {
            item["projection_id"]: item["projection_fingerprint"]
            for item in projection_refs
        }
        output = {
            "projection_ids": projection_ids,
            "projection_fingerprints": fingerprints,
            "projection_refs": projection_refs,
            "component_identity": projection_refs[0] if len(projection_refs) == 1 else {"projection_ids": projection_ids, "projection_refs": projection_refs},
            "fingerprint": stable_hash(repr(projection_refs)),
        }
        return self.ok_result(
            kernel_function="create_custom_projection",
            capability_status="implemented_in_pipeline",
            output_refs=output,
        )
