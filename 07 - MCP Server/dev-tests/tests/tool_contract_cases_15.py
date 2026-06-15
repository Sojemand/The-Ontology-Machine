from __future__ import annotations

from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "read_working_release",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"]},
            edit_calls=lambda _p: [("normalizer", {"action": "read_release_package"})],
        ),
        GoldenCase(
            "list_working_release_profiles",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"]},
            edit_calls=lambda _p: [("normalizer", {"action": "list_projections"})],
        ),
        GoldenCase(
            "read_working_release_profile",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"], "projection_id": "finance.default.v1"},
            edit_calls=lambda _p: [("normalizer", {"action": "read_projection", "projection_id": "finance.default.v1"})],
        ),
        GoldenCase(
            "validate_working_release",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"], "target_locale": "en"},
            edit_calls=lambda _p: [("normalizer", {"action": "validate_release_package", "target_locale": "en"})],
        ),
        GoldenCase(
            "compile_working_release",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"], "target_locale": "en"},
            edit_calls=lambda _p: [("normalizer", {"action": "compile_release_package", "target_locale": "en"})],
        ),
        GoldenCase(
            "preview_working_release_impact",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"]},
            edit_calls=lambda _p: [("normalizer", {"action": "preview_impact"})],
        ),
        GoldenCase(
            "create_working_release_package",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "default_runtime_locale": "de",
                "projection_ids": ["finance.default.v1"],
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "create_release_package",
                        "default_runtime_locale": "de",
                        "projection_ids": ["finance.default.v1"],
                    },
                )
            ],
        ),
        GoldenCase(
            "export_working_release",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "output_path": p["working_release_path"],
                "target_locale": "en",
            },
            edit_calls=lambda p: [
                (
                    "normalizer",
                    {
                        "action": "export_semantic_release",
                        "output_path": p["working_release_path"],
                        "target_locale": "en",
                    },
                )
            ],
        ),
        GoldenCase(
            "create_locale_scaffold",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "source_locale": "en",
                "target_locale": "fr",
                "overwrite_existing": True,
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "create_locale_scaffold",
                        "source_locale": "en",
                        "target_locale": "fr",
                        "overwrite_existing": True,
                    },
                )
            ],
        ),
    ]
