"""Descriptor metadata for guided Orchestrator policy surfaces."""
from __future__ import annotations

from ..policy_store.types import (
    ARTIFACT_PUBLICATION_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    ROUTE_INTAKE_SURFACE_ID,
)

_GROUPS = {
    ROUTE_INTAKE_SURFACE_ID: (
        ("Route Families", ("route_families", "enabled_route_families", "unrouted_error_family")),
        ("Suffix Groups", ("suffix_groups",)),
        ("PDF Handling", ("pdf_classifications", "pdf_routing")),
    ),
    EXECUTION_SURFACE_ID: (
        ("Pipeline Stages", ("pipeline_stage_names", "global_required_modules")),
        ("Timeouts", ("healthcheck_timeout_seconds", "projection_catalog_timeout_seconds", "operation_timeouts_seconds")),
        ("Module Contracts", ("modules",)),
    ),
    HEALTH_DEPENDENCY_SURFACE_ID: (
        ("Scope Profiles", ("scope_profiles",)),
        ("Fallback", ("fallback_for_other_scopes",)),
    ),
    ARTIFACT_PUBLICATION_SURFACE_ID: (
        ("Workspace Layout", ("pipeline_state_dir_name", "run_workspace_dir_name", "error_root_name", "legacy_error_root_names")),
        ("Route Layout", ("route_folder_map", "route_artifact_subdirs")),
        ("Publication Names", ("publication_names", "request_file_names")),
    ),
}

_FIELD_LABELS = {
    ROUTE_INTAKE_SURFACE_ID: {
        "route_families": "Known Route Families",
        "enabled_route_families": "Enabled Route Families",
        "unrouted_error_family": "Unrouted Error Family",
        "suffix_groups": "Suffix Groups",
        "pdf_classifications": "PDF Classification Labels",
        "pdf_routing": "PDF Routing Targets",
    },
    EXECUTION_SURFACE_ID: {
        "pipeline_stage_names": "Pipeline Stage Names",
        "global_required_modules": "Global Required Modules",
        "healthcheck_timeout_seconds": "Healthcheck Timeout (Seconds)",
        "projection_catalog_timeout_seconds": "Projection Catalog Timeout (Seconds)",
        "modules": "Per-Module Contract Policy",
        "operation_timeouts_seconds": "Operation Timeouts (Seconds)",
    },
    HEALTH_DEPENDENCY_SURFACE_ID: {
        "scope_profiles": "Scope Profiles",
        "fallback_for_other_scopes": "Fallback for Other Scopes",
    },
    ARTIFACT_PUBLICATION_SURFACE_ID: {
        "pipeline_state_dir_name": "Pipeline State Directory Name",
        "run_workspace_dir_name": "Run Workspace Directory Name",
        "route_folder_map": "Route Folder Map",
        "error_root_name": "Error Root Name",
        "legacy_error_root_names": "Legacy Error Root Names",
        "route_artifact_subdirs": "Route Artifact Subdirectories",
        "publication_names": "Publication Names",
        "request_file_names": "Request File Names",
    },
}

_FIELD_HELP = {
    ROUTE_INTAKE_SURFACE_ID: {
        "route_families": "Defines the canonical route labels the orchestrator knows about.",
        "enabled_route_families": "Controls which saved route families future intake decisions may activate.",
        "unrouted_error_family": "Names the error bucket used when no route can be resolved.",
        "suffix_groups": "Maps file suffixes into image, file, table, and PDF intake buckets.",
        "pdf_classifications": "Stores the saved labels used for born-digital and scan PDF classification.",
        "pdf_routing": "Maps each saved PDF class to the downstream route family and module handoff.",
    },
    EXECUTION_SURFACE_ID: {
        "pipeline_stage_names": "Defines the saved pipeline stage labels used in plans and reporting.",
        "global_required_modules": "Lists modules that every normal pipeline run must have available.",
        "healthcheck_timeout_seconds": "Sets the saved timeout budget for orchestrator healthcheck calls.",
        "projection_catalog_timeout_seconds": "Sets the saved timeout budget for projection catalog work.",
        "modules": "Stores display name, stage role, and required actions per downstream module.",
        "operation_timeouts_seconds": "Stores the saved timeout budget for each downstream contract action.",
    },
    HEALTH_DEPENDENCY_SURFACE_ID: {
        "scope_profiles": "Defines required dependency profiles by orchestrator scope and module.",
        "fallback_for_other_scopes": "Defines the saved dependency fallback when no scope-specific profile exists.",
    },
    ARTIFACT_PUBLICATION_SURFACE_ID: {
        "pipeline_state_dir_name": "Defines where future pipeline state snapshots are materialized.",
        "run_workspace_dir_name": "Defines the saved root name for per-run workspaces under pipeline state.",
        "route_folder_map": "Maps route families to their saved publication folder names.",
        "error_root_name": "Defines the saved root folder name for published error bundles.",
        "legacy_error_root_names": "Lists legacy error-root folder names that remain recognized.",
        "route_artifact_subdirs": "Defines the saved artifact subdirectory order below each route folder.",
        "publication_names": "Stores the publication folder names for each artifact family.",
        "request_file_names": "Stores saved publication filenames for generated request artifacts.",
    },
}


def descriptor_metadata(surface_id: str) -> dict:
    return {
        "editor_kind": "nested_policy",
        "field_groups": [{"label": label, "fields": list(fields)} for label, fields in _GROUPS[surface_id]],
        "field_labels": dict(_FIELD_LABELS[surface_id]),
        "field_help": dict(_FIELD_HELP[surface_id]),
    }
