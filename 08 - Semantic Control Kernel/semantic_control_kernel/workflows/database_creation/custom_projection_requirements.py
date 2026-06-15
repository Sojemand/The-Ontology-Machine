from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker, DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    create_blocker,
    validate_selected_sample_refs,
)


def validate_projection_samples(
    *,
    target: DatabaseCreationTarget | None,
    sample_refs: Sequence[Mapping[str, Any]],
) -> DatabaseCreationBlocker | None:
    return validate_selected_sample_refs(
        target=target,
        sample_refs=sample_refs,
        step_id="proj_require_samples",
        sample_subject="projection",
    )


def validate_projection_taxonomy_ref(taxonomy_ref: Mapping[str, Any] | None) -> DatabaseCreationBlocker | None:
    if not taxonomy_ref:
        return create_blocker(
            step_id="proj_require_taxonomy",
            function_or_route="create_custom_projection_path",
            blocker_code="input_missing",
            recovery_state_class="semantic_release_incomplete_staged",
            summary="Custom projection creation requires a staged, attached or active taxonomy resolved by Kernel state.",
        )
    for key in ("taxonomy_id", "taxonomy_fingerprint"):
        if not taxonomy_ref.get(key):
            return create_blocker(
                step_id="proj_require_taxonomy",
                function_or_route="create_custom_projection_path",
                blocker_code="input_missing",
                recovery_state_class="semantic_release_incomplete_staged",
                summary=f"Custom projection creation requires taxonomy proof field {key}.",
            )
    return None


def projection_validation_blocker(step_id: str, summary: str) -> DatabaseCreationBlocker:
    return create_blocker(
        step_id=step_id,
        function_or_route="validate_projections_against_taxonomy",
        blocker_code="projection_taxonomy_invalid",
        recovery_state_class="semantic_release_incomplete_staged",
        summary=summary,
    )
