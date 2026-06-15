from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _artifact_properties, _enum, _tool


def workspace_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "inspect_active_corpus",
            "Inspect Corpus Builder semantic status for an explicit or default DB.",
            {"corpus_db_path": {"type": "string"}},
        ),
        _tool(
            "activate_corpus_context",
            "Select one existing corpus DB as the current pipeline context through owner contracts. This only registers paths and does not activate an extraction pack, release, profile, or language.",
            {
                "corpus_db_path": {"type": "string"},
                "corpus_output_folder": {"type": "string"},
                "artifact_folder": {"type": "string"},
                "input_folder": {"type": "string", "description": "Optional existing folder that the Orchestrator should use as the document input folder."},
            },
            required=("corpus_db_path",),
        ),
        _tool(
            "create_empty_corpus_db",
            "Create an empty SQLite corpus DB through Corpus Builder only. This does not register context, activate an extraction pack, or select a language.",
            {
                "corpus_db_path": {"type": "string"},
                "corpus_output_folder": {"type": "string"},
            },
            required=("corpus_db_path",),
        ),
        _tool(
            "prepare_pipeline_workspace_root",
            "Create only the expected local pipeline workspace folder structure. This does not create a DB, register context, export a release, or activate anything.",
            {
                "artifact_folder": {"type": "string"},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "write_workspace_release_change_confirmation",
            "Write only the workspace-local confirmation artifact required for an already reviewed release change. This does not run preflight, activate a release, switch context, or backfill.",
            {
                "artifact_folder": {"type": "string"},
                "database_name": {"type": "string"},
                "activation_preflight_result": {"type": "object"},
                "activation_decision": {"type": "string", "enum": ["activate_only", "activate_and_backfill"]},
                "confirm_release_change": {"type": "boolean"},
                "confirmation_artifact_path": {"type": "string"},
            },
            required=(
                "artifact_folder",
                "database_name",
                "activation_preflight_result",
                "activation_decision",
                "confirm_release_change",
            ),
        ),
        _tool(
            "write_workspace_db_reset_confirmation",
            "Write only the workspace-local confirmation artifact for reset_active_corpus_db. This does not reset the DB, export a release, activate a release, or switch context.",
            {
                "artifact_folder": {"type": "string"},
                "database_name": {"type": "string"},
                "confirm_reset": {"type": "boolean"},
                "reset_reason": {"type": "string"},
                "confirmation_artifact_path": {"type": "string"},
            },
            required=("artifact_folder", "database_name", "confirm_reset", "reset_reason"),
        ),
        _tool(
            "verify_workspace_active_release",
            "Read and verify the active semantic release on a workspace DB after activation. This does not export, activate, reset, or switch context.",
            {
                "artifact_folder": {"type": "string"},
                "database_name": {"type": "string"},
                "language": {"type": "string", "description": "Expected active runtime locale."},
                "projection_ids": {"type": "array", "items": {"type": "string"}},
            },
            required=("artifact_folder", "database_name", "language"),
        ),
        _tool(
            "read_revision_candidate_release",
            "Read and summarize an already exported candidate semantic release. This does not create, validate, preflight, activate, or persist any new release truth.",
            {
                "release_path": {"type": "string"},
            },
            required=("release_path",),
        ),
        _tool(
            "inspect_release_revision_context",
            "Inspect an existing corpus DB and its active semantic release for release-revision review. This is read-only and does not run activation preflight.",
            {
                "corpus_db_path": {"type": "string"},
            },
            required=("corpus_db_path",),
        ),
        _tool(
            "classify_release_revision",
            "Classify a candidate release against previously inspected DB/runtime state and an explicit activation_preflight result or error. This is pure classification and makes no owner calls.",
            {
                "database_state": {"type": "object"},
                "candidate_release": {"type": "object"},
                "active_release": {"type": "object"},
                "activation_preflight_result": {"type": "object"},
                "activation_preflight_error": {"type": "string"},
            },
            required=("database_state", "candidate_release"),
        ),
    ]
