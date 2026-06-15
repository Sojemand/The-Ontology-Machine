from __future__ import annotations

from semantic_control_kernel.workflows.database_creation.custom_release_activation_steps import (
    step_activate_custom_release,
    step_attach_custom_release,
)
from semantic_control_kernel.workflows.database_creation.custom_release_materialization_steps import (
    step_create_custom_release,
    step_write_custom_release,
)
from semantic_control_kernel.workflows.database_creation.default_projectionless_steps import (
    step_remove_default_projections,
)
from semantic_control_kernel.workflows.database_creation.default_release_steps import (
    step_activate_default_release,
    step_attach_default_release,
    step_export_default_release,
    step_write_default_release,
)
from semantic_control_kernel.workflows.database_creation.incomplete_state_steps import (
    step_persist_incomplete_state,
)
from semantic_control_kernel.workflows.database_creation.projection_authoring_steps import (
    step_projection_authoring_view,
    step_projection_llm_path,
)
from semantic_control_kernel.workflows.database_creation.projection_materialization_steps import (
    step_create_custom_projection,
    step_stage_custom_projection,
    step_validate_custom_projection,
)
from semantic_control_kernel.workflows.database_creation.projection_requirements import (
    step_projection_require_samples,
    step_projection_require_taxonomy,
)
from semantic_control_kernel.workflows.database_creation.provisioning import (
    step_collect_target,
    step_create_artifact_tree,
    step_create_empty_database,
    step_store_artifact_tree,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    create_blocker,
)
from semantic_control_kernel.workflows.database_creation.step_support import stop_step
from semantic_control_kernel.workflows.database_creation.taxonomy_steps import (
    step_create_custom_taxonomy,
    step_stage_custom_taxonomy,
    step_tax_require_samples,
    step_taxonomy_llm_path,
)


_STEP_HANDLERS = {
    "dc_collect_target": step_collect_target,
    "dc_create_artifact_tree": step_create_artifact_tree,
    "dc_store_artifact_tree": step_store_artifact_tree,
    "dc_create_empty_database": step_create_empty_database,
    "dc_export_default_release": step_export_default_release,
    "dc_write_default_release": step_write_default_release,
    "dc_attach_default_release": step_attach_default_release,
    "dc_remove_default_projections": step_remove_default_projections,
    "dc_activate_default_release": step_activate_default_release,
    "tax_require_samples": step_tax_require_samples,
    "tax_analyze_samples": step_taxonomy_llm_path,
    "tax_create_custom_taxonomy": step_create_custom_taxonomy,
    "tax_stage_custom_taxonomy": step_stage_custom_taxonomy,
    "proj_require_taxonomy": step_projection_require_taxonomy,
    "proj_require_samples": step_projection_require_samples,
    "proj_build_authoring_view": step_projection_authoring_view,
    "proj_analyze_samples": step_projection_llm_path,
    "proj_create_custom_projection": step_create_custom_projection,
    "proj_validate_projection": step_validate_custom_projection,
    "proj_stage_custom_projection": step_stage_custom_projection,
    "rel_create_custom_release": step_create_custom_release,
    "rel_write_custom_release": step_write_custom_release,
    "rel_attach_custom_release": step_attach_custom_release,
    "rel_activate_custom_release": step_activate_custom_release,
    "rel_persist_incomplete_state": step_persist_incomplete_state,
}


def run_database_creation_step(
    runtime,
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    step_id: str,
) -> None:
    handler = _STEP_HANDLERS.get(step_id)
    if handler is None:
        stop_step(
            repository,
            execution,
            create_blocker(
                step_id=step_id,
                function_or_route=step_id,
                blocker_code="unknown_state",
                summary=f"Phase 9 route step {step_id} is not implemented.",
            ),
        )
        return
    handler(runtime, repository, execution)
