"""Workflow helpers for orchestrator contract actions."""

from __future__ import annotations

import os

from . import source_inspection
from .workflow_corpus_context import activate_corpus_context_action
from .workflow_embeddings import (
    _OWNER_EMBEDDING_OK_STATUSES,
    _embedding_owner_result,
    _selected_database_path,
    embeddings_action,
)
from .workflow_run import _owner_input_hashes, _relative_targets, reset_action, reset_pipeline_logs_action, run_action
from .workflow_snapshot import (
    SNAPSHOT_REPLACE_ATTEMPTS,
    SNAPSHOT_REPLACE_RETRY_SECONDS,
    SNAPSHOT_TRANSIENT_WINERRORS,
    _error_case_original_files,
    _error_cases_folder_snapshot,
    _error_cases_root,
    _is_retryable_snapshot_replace_error,
    _replace_snapshot_with_retry,
    _snapshot_file_writer,
)

inspect_source_document_sample_action = source_inspection.inspect_source_document_sample_action


def error_response(message: str) -> dict:
    return {"status": "error", "reason": str(message)}


def healthcheck(*, ensure_startup_prerequisites) -> dict:
    try:
        ensure_startup_prerequisites()
    except Exception as exc:
        return {
            "status": "error",
            "healthy": False,
            "message": str(exc),
            "dependencies": [],
        }
    return {"status": "ok", "healthy": True, "message": "", "dependencies": []}


__all__ = [
    "SNAPSHOT_REPLACE_ATTEMPTS",
    "SNAPSHOT_REPLACE_RETRY_SECONDS",
    "SNAPSHOT_TRANSIENT_WINERRORS",
    "_OWNER_EMBEDDING_OK_STATUSES",
    "_embedding_owner_result",
    "_error_case_original_files",
    "_error_cases_folder_snapshot",
    "_error_cases_root",
    "_is_retryable_snapshot_replace_error",
    "_owner_input_hashes",
    "_relative_targets",
    "_replace_snapshot_with_retry",
    "_selected_database_path",
    "_snapshot_file_writer",
    "activate_corpus_context_action",
    "embeddings_action",
    "error_response",
    "healthcheck",
    "inspect_source_document_sample_action",
    "os",
    "reset_action",
    "reset_pipeline_logs_action",
    "run_action",
    "source_inspection",
]
