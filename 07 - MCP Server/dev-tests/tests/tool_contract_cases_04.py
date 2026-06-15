from __future__ import annotations

from tests.tool_contract_matrix_helpers import _reset_workspace_paths, _working_workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "write_workspace_release_change_confirmation",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "database_name": "Fantasy Story",
                "activation_decision": "activate_and_backfill",
                "confirm_release_change": True,
                "activation_preflight_result": _same_master_preflight(p),
            },
        ),
        GoldenCase(
            "write_workspace_db_reset_confirmation",
            lambda p: {
                "artifact_folder": p["reset_workspace_artifact_root"],
                "database_name": "Fantasy Story",
                "confirm_reset": True,
                "reset_reason": "test reset",
            },
        ),
        GoldenCase(
            "verify_workspace_active_release",
            lambda p: {
                "artifact_folder": p["reset_workspace_artifact_root"],
                "database_name": "Fantasy Story",
                "language": "de",
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "read_active_semantic_release", "corpus_db_path": _reset_workspace_paths(p)["db"]},
                ),
            ],
        ),
    ]


def _same_master_preflight(paths: dict[str, str]) -> dict:
    workspace = _working_workspace_paths(paths)
    return {
        "requires_confirmation": True,
        "db_changes": {"projection_drift_documents": 0},
        "confirmation_artifact_template": {
            "artifact_version": "semantic_activation_confirmation_v1",
            "corpus_db_path": workspace["db"],
            "release_path": workspace["release"],
            "expected_current_snapshot_id": "old",
            "expected_new_snapshot_id": "new",
            "expected_release_fingerprint": "sha256:new",
            "expected_master_taxonomy_release_id": "sha256:same",
            "expected_runtime_locale": "de",
            "decision": "activate_only",
        },
    }
