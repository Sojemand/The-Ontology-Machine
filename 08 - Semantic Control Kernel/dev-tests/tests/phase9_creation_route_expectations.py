from __future__ import annotations

import json
from pathlib import Path

EXPECTED = {
    "empty_database_no_semantic_release": ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database", "dc_final_notice"),
    "empty_database_default_taxonomy_no_projections": ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database", "dc_export_default_release", "dc_write_default_release", "dc_attach_default_release", "dc_remove_default_projections", "rel_persist_incomplete_state", "dc_final_notice"),
    "empty_database_default_taxonomy_default_projections": ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database", "dc_export_default_release", "dc_write_default_release", "dc_attach_default_release", "dc_activate_default_release", "dc_final_notice"),
    "empty_database_default_taxonomy_custom_projections": ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database", "dc_export_default_release", "dc_write_default_release", "dc_attach_default_release", "dc_remove_default_projections", "proj_require_taxonomy", "proj_require_samples", "proj_build_authoring_view", "proj_analyze_samples", "proj_create_proposal", "proj_build_update_state", "proj_create_custom_projection", "proj_validate_projection", "proj_stage_custom_projection", "rel_create_custom_release", "rel_write_custom_release", "rel_attach_custom_release", "rel_activate_custom_release", "dc_final_notice"),
    "empty_database_custom_taxonomy_no_projections": ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database", "tax_require_samples", "tax_analyze_samples", "tax_create_proposal", "tax_build_update_state", "tax_create_custom_taxonomy", "tax_stage_custom_taxonomy", "rel_persist_incomplete_state", "dc_final_notice"),
    "empty_database_custom_taxonomy_custom_projections": ("dc_collect_target", "dc_create_artifact_tree", "dc_store_artifact_tree", "dc_create_empty_database", "tax_require_samples", "tax_analyze_samples", "tax_create_proposal", "tax_build_update_state", "tax_create_custom_taxonomy", "tax_stage_custom_taxonomy", "proj_require_taxonomy", "proj_require_samples", "proj_build_authoring_view", "proj_analyze_samples", "proj_create_proposal", "proj_build_update_state", "proj_create_custom_projection", "proj_validate_projection", "proj_stage_custom_projection", "rel_create_custom_release", "rel_write_custom_release", "rel_attach_custom_release", "rel_activate_custom_release", "dc_final_notice"),
    "create_custom_taxonomy_path": ("tax_require_samples", "tax_analyze_samples", "tax_create_proposal", "tax_build_update_state", "tax_create_custom_taxonomy", "dc_final_notice"),
    "create_custom_projection_path": ("proj_require_taxonomy", "proj_require_samples", "proj_build_authoring_view", "proj_analyze_samples", "proj_create_proposal", "proj_build_update_state", "proj_create_custom_projection", "proj_validate_projection", "dc_final_notice"),
}

MODULE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_CREATION_GOLDEN_PATH = MODULE_ROOT / "dev-tests" / "fixtures" / "phase9" / "frozen_primary_creation_workflows.json"
FROZEN_CREATION_GOLDEN = json.loads(FROZEN_CREATION_GOLDEN_PATH.read_text(encoding="utf-8"))
FROZEN_CREATION_TOOLS = tuple(entry["workflow_tool"] for entry in FROZEN_CREATION_GOLDEN["workflows"])
