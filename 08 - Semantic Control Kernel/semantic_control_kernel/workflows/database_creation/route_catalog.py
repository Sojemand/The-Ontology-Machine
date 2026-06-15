from __future__ import annotations

from types import MappingProxyType

from semantic_control_kernel.workflows.database_creation.route_types import DatabaseCreationRoute


WORKFLOW_ENTRIES: tuple[str, ...] = (
    "empty_database_no_semantic_release",
    "empty_database_default_taxonomy_no_projections",
    "empty_database_default_taxonomy_default_projections",
    "empty_database_default_taxonomy_custom_projections",
    "empty_database_custom_taxonomy_no_projections",
    "empty_database_custom_taxonomy_custom_projections",
    "create_custom_taxonomy_path",
    "create_custom_projection_path",
)

DRIFT_PREFLIGHT = MappingProxyType(
    {
        "status": "drift_preflight: build_plan_authority_applied",
        "items": (
            {
                "document": "05_database_creation_workflows.md",
                "detail": "empty_database_custom_taxonomy_no_projections names write_semantic_release after staging taxonomy.",
                "applied_authority": "Phase 9 build-ready route uses rel_persist_incomplete_state and keeps taxonomy-only releases blocked/resumable.",
            },
        ),
    }
)

PROVISION_EMPTY_DATABASE = ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database")
DEFAULT_RELEASE_ATTACH = ("dc_export_default_release", "dc_write_default_release", "dc_attach_default_release")
TAXONOMY_AUTHORING = ("tax_require_samples", "tax_analyze_samples", "tax_create_proposal", "tax_build_update_state", "tax_create_custom_taxonomy")
STAGE_CUSTOM_TAXONOMY = ("tax_stage_custom_taxonomy",)
PROJECTION_AUTHORING = ("proj_require_taxonomy", "proj_require_samples", "proj_build_authoring_view", "proj_analyze_samples", "proj_create_proposal", "proj_build_update_state", "proj_create_custom_projection", "proj_validate_projection")
STAGE_CUSTOM_PROJECTION = ("proj_stage_custom_projection",)
CUSTOM_RELEASE_ACTIVATION = ("rel_create_custom_release", "rel_write_custom_release", "rel_attach_custom_release", "rel_activate_custom_release")
DEFAULT_PROJECTIONLESS_STATE = ("dc_remove_default_projections", "rel_persist_incomplete_state")
FINAL_NOTICE = ("dc_final_notice",)

_r = DatabaseCreationRoute

ROUTES: tuple[DatabaseCreationRoute, ...] = (
    _r("empty_database_no_semantic_release", PROVISION_EMPTY_DATABASE + FINAL_NOTICE, "no_semantic_release", "release creation may resume only from Kernel state."),
    _r("empty_database_default_taxonomy_no_projections", PROVISION_EMPTY_DATABASE + DEFAULT_RELEASE_ATTACH + DEFAULT_PROJECTIONLESS_STATE + FINAL_NOTICE, "semantic_release_incomplete", "create_custom_projection_path is allowed only through matching Kernel resume state."),
    _r("empty_database_default_taxonomy_default_projections", PROVISION_EMPTY_DATABASE + DEFAULT_RELEASE_ATTACH + ("dc_activate_default_release",) + FINAL_NOTICE, "semantic_release_active", "no creation resume required."),
    _r("empty_database_default_taxonomy_custom_projections", PROVISION_EMPTY_DATABASE + DEFAULT_RELEASE_ATTACH + ("dc_remove_default_projections",) + PROJECTION_AUTHORING + STAGE_CUSTOM_PROJECTION + CUSTOM_RELEASE_ACTIVATION + FINAL_NOTICE, "semantic_release_active", "resume from last completed projection or release step when blocked after DB creation."),
    _r("empty_database_custom_taxonomy_no_projections", PROVISION_EMPTY_DATABASE + TAXONOMY_AUTHORING + STAGE_CUSTOM_TAXONOMY + ("rel_persist_incomplete_state",) + FINAL_NOTICE, "semantic_release_incomplete", "create_custom_projection_path is valid only against the staged taxonomy."),
    _r("empty_database_custom_taxonomy_custom_projections", PROVISION_EMPTY_DATABASE + TAXONOMY_AUTHORING + STAGE_CUSTOM_TAXONOMY + PROJECTION_AUTHORING + STAGE_CUSTOM_PROJECTION + CUSTOM_RELEASE_ACTIVATION + FINAL_NOTICE, "semantic_release_active", "projection analysis may reuse taxonomy analysis only when sample identity matches."),
    _r(
        "create_custom_taxonomy_path",
        TAXONOMY_AUTHORING + FINAL_NOTICE,
        "unchanged",
        "parent or resume invocation may stage the taxonomy and mark projections missing.",
        optional_step_ids=("tax_stage_custom_taxonomy", "rel_persist_incomplete_state"),
    ),
    _r(
        "create_custom_projection_path",
        PROJECTION_AUTHORING + FINAL_NOTICE,
        "unchanged",
        "parent or resume invocation may stage projections and finalize a custom release.",
        optional_step_ids=(
            "proj_stage_custom_projection",
            "rel_create_custom_release",
            "rel_write_custom_release",
            "rel_attach_custom_release",
            "rel_activate_custom_release",
        ),
    ),
)

ROUTE_BY_TOOL = MappingProxyType({route.workflow_tool: route for route in ROUTES})
