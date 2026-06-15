from __future__ import annotations

from tests.tool_contract_matrix_types import GoldenCase

BOOTSTRAP_ARGS = {
    "goal": "Fantasy story archive",
    "must_keep": "characters and places",
    "noise_tolerance": "medium",
}


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "review_bootstrap_release",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"], **BOOTSTRAP_ARGS},
            edit_calls=lambda _p: [("normalizer", {"action": "review_bootstrap_release", **BOOTSTRAP_ARGS})],
        ),
        GoldenCase(
            "apply_bootstrap_release",
            lambda p: {"artifact_folder": p["working_workspace_artifact_root"], **BOOTSTRAP_ARGS, "user_confirmed": True},
            edit_calls=lambda _p: [("normalizer", {"action": "bootstrap_release_package", **BOOTSTRAP_ARGS})],
        ),
        GoldenCase(
            "review_data_informed_release",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "structured_sample_path": p["structured_sample"],
                "expected_normalized_path": p["expected_normalized"],
                "original_reference_path": p["sample_document"],
                "sample_label": "Fantasy sample",
            },
            edit_calls=lambda p: [
                (
                    "normalizer",
                    {
                        "action": "review_data_informed_release",
                        "structured_sample_path": p["structured_sample"],
                        "expected_normalized_path": p["expected_normalized"],
                        "original_reference_path": p["sample_document"],
                        "sample_label": "Fantasy sample",
                    },
                )
            ],
        ),
        GoldenCase(
            "refine_working_release_from_sample",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "structured_sample_path": p["structured_sample"],
                "expected_normalized_path": p["expected_normalized"],
                "sample_label": "Fantasy sample",
                "user_confirmed": True,
            },
            edit_calls=lambda p: [
                (
                    "normalizer",
                    {
                        "action": "refine_release_package",
                        "structured_sample_path": p["structured_sample"],
                        "expected_normalized_path": p["expected_normalized"],
                        "sample_label": "Fantasy sample",
                    },
                )
            ],
        ),
    ]
