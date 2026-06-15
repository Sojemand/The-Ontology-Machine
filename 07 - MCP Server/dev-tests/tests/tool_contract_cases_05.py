from __future__ import annotations

from tests.tool_contract_matrix_helpers import _artifact_args, _reset_workspace_paths, _support_incident, _working_workspace_paths, _workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "inspect_active_workspace_status",
            lambda _p: {},
        ),
        GoldenCase(
            "inspect_current_environment_status",
            lambda _p: {},
        ),
        GoldenCase(
            "run_active_pipeline",
            lambda _p: {"mode": "batch"},
            product_calls=lambda p: [
                (
                    "orchestrator",
                    {
                        "action": "run",
                        "ui_state": {
                            "input_folder": p["run_input"],
                            "artifact_folder": p["run_artifact_root"],
                            "corpus_output_folder": p["run_corpus"],
                            "selected_corpus_db_path": p["run_db"],
                            "semantic_release_mode": "database_default",
                            "semantic_release_path": "",
                            "mode": "batch",
                        },
                    },
                )
            ],
        ),
        GoldenCase(
            "start_active_pipeline_run",
            lambda _p: {"mode": "batch"},
        ),
        GoldenCase(
            "inspect_active_pipeline_run",
            lambda _p: {},
        ),
        GoldenCase(
            "cancel_active_pipeline_run",
            lambda _p: {},
        ),
        GoldenCase(
            "preview_active_corpus_source_reimport",
            lambda _p: {},
        ),
        GoldenCase(
            "prepare_active_corpus_source_reimport",
            lambda _p: {"user_confirmed": True},
        ),
        GoldenCase(
            "read_active_semantic_release",
            lambda p: {"corpus_db_path": p["active_db"]},
            product_calls=lambda p: [
                ("corpus_builder", {"action": "read_active_semantic_release", "corpus_db_path": p["active_db"]})
            ],
        ),
        GoldenCase(
            "reset_active_corpus_db",
            lambda p: {"corpus_db_path": p["active_db"], "confirmation_artifact_path": p["confirmation"]},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "reset_active_corpus_db",
                        "corpus_db_path": p["active_db"],
                        "confirmation_artifact_path": p["confirmation"],
                    },
                )
            ],
        ),
        GoldenCase(
            "load_semantic_release",
            lambda p: {"release_path": p["release_path"], "corpus_db_path": p["active_db"]},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "load_semantic_release", "release_path": p["release_path"], "corpus_db_path": p["active_db"]},
                )
            ],
        ),
        GoldenCase(
            "semantic_audit",
            lambda p: {"corpus_db_path": p["active_db"]},
            product_calls=lambda p: [("corpus_builder", {"action": "semantic_audit", "corpus_db_path": p["active_db"]})],
        ),
        GoldenCase(
            "activation_preflight",
            lambda p: {"release_path": p["release_path"], "corpus_db_path": p["active_db"]},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "activation_preflight", "release_path": p["release_path"], "corpus_db_path": p["active_db"]},
                )
            ],
        ),
        GoldenCase(
            "activate_release_on_existing_db",
            lambda p: {
                "release_path": p["release_path"],
                "corpus_db_path": p["active_db"],
                "confirmation_artifact_path": p["activation_confirmation"],
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "activate_semantic_release",
                        "release_path": p["release_path"],
                        "corpus_db_path": p["active_db"],
                        "confirmation_artifact_path": p["activation_confirmation"],
                        "write_global_mirrors": False,
                    },
                ),
            ],
        ),
    ]
