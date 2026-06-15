from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.types.interaction import USER_INTERACTION_MAPPINGS


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = PIPELINE_ROOT / "Semantic Kernel SPEC" / "08_user_function_surface.md"

EXPECTED_USER_FUNCTIONS = {
    "choose_artifact_root_folder",
    "name_artifact_root_folder",
    "name_database",
    "select_sample_files",
    "use_current_active_database",
    "use_custom_database_path",
    "choose_merge_database_count",
    "choose_databases_to_merge",
    "choose_new_artifact_root_folder",
    "choose_merge_projection_mode",
    "user_confirmation",
}

EXPECTED_MAPPINGS = {
    "choose_artifact_root_folder": ("selection", "folder_picker", ("path_value",), ("artifact_root_path_hash",), ("workflow_run_id",), "selection_short"),
    "name_artifact_root_folder": ("input", "folder_create_picker", ("path_value", "text_value"), ("artifact_root_path_hash",), ("parent_path_hash",), "selection_short"),
    "name_database": ("input", "text_input", ("text_value",), ("artifact_root_path_hash",), ("database_path_hash",), "selection_short"),
    "select_sample_files": ("confirmation", "input_presence_confirmation", ("confirmation_decision",), ("artifact_root_path_hash", "input_path_hash", "database_path_hash"), (), "confirmation_long_running"),
    "use_current_active_database": ("selection", "active_database_choice", ("choice_id",), ("database_path_hash", "database_id", "artifact_root_path_hash"), (), "selection_short"),
    "use_custom_database_path": ("selection", "database_path_picker", ("path_value",), ("database_path_hash",), ("database_id", "artifact_root_path_hash"), "selection_short"),
    "choose_merge_database_count": ("input", "text_input", ("text_value",), ("source_database_set_hash",), ("database_path_hash",), "selection_short"),
    "choose_databases_to_merge": ("selection", "database_list_picker", ("selected_database_paths",), ("source_database_set_hash", "database_path_hash"), ("database_id",), "selection_long"),
    "choose_new_artifact_root_folder": ("selection", "folder_create_picker", ("path_value",), ("artifact_root_path_hash", "target_hash"), (), "selection_short"),
    "choose_merge_projection_mode": ("selection", "update_mode_choice", ("choice_id",), ("source_database_set_hash", "target_hash"), (), "selection_short"),
    "user_confirmation": ("confirmation", "generic_confirmation", ("confirmation_decision",), (), (), "confirmation_destructive"),
}


def test_phase6_user_mapping_covers_spec_user_functions() -> None:
    spec_text = SPEC_PATH.read_text(encoding="utf-8")

    for function_name in EXPECTED_USER_FUNCTIONS:
        assert function_name in spec_text
    assert set(USER_INTERACTION_MAPPINGS) == EXPECTED_USER_FUNCTIONS


def test_every_phase6_mapping_has_required_contract_shape() -> None:
    for function_name, mapping in USER_INTERACTION_MAPPINGS.items():
        expected_kind, expected_dialog, expected_values, expected_required, expected_optional, expected_expiration = EXPECTED_MAPPINGS[function_name]
        assert mapping.interaction_function == function_name
        assert mapping.interaction_kind == expected_kind
        assert mapping.dialog_type == expected_dialog
        assert mapping.response_value_fields == expected_values
        assert mapping.required_target_identity_fields == expected_required
        assert mapping.optional_target_identity_fields == expected_optional
        assert mapping.expiration_policy_id == expected_expiration
