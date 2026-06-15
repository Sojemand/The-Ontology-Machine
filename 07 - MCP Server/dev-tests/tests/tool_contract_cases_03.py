from __future__ import annotations

from tests.tool_contract_matrix_helpers import _artifact_args, _reset_workspace_paths, _support_incident, _working_workspace_paths, _workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "create_empty_corpus_db",
            lambda p: {"corpus_db_path": p["fresh_db"], "corpus_output_folder": p["corpus_root"]},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "create_empty_corpus_db", "corpus_db_path": p["fresh_db"], "activate_context": False},
                ),
            ],
        ),
        GoldenCase(
            "prepare_pipeline_workspace_root",
            lambda p: {"artifact_folder": p["workspace_artifact_root"]},
        ),
    ]
