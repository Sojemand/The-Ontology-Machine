from __future__ import annotations

from tests.tool_contract_matrix_helpers import _reset_workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "read_revision_candidate_release",
            lambda p: {"release_path": p["release_path"]},
        ),
        GoldenCase(
            "inspect_release_revision_context",
            lambda p: {"corpus_db_path": _reset_workspace_paths(p)["db"]},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "semantic_status", "corpus_db_path": _reset_workspace_paths(p)["db"]},
                ),
                (
                    "corpus_builder",
                    {"action": "read_active_semantic_release", "corpus_db_path": _reset_workspace_paths(p)["db"]},
                ),
            ],
        ),
        GoldenCase(
            "classify_release_revision",
            lambda _p: {
                "database_state": {"exists": True, "state": "empty", "document_count": 0},
                "candidate_release": {
                    "fingerprint": "sha256:candidate",
                    "master_taxonomy_release_id": "sha256:same",
                    "projection_ids": ["fantasy.story.default.v1"],
                },
                "active_release": {"fingerprint": "sha256:active", "master_taxonomy_release_id": "sha256:same"},
                "activation_preflight_result": {"requires_confirmation": False},
            },
        ),
    ]
