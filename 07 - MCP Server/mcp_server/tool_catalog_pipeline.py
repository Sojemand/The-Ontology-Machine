from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _artifact_properties, _enum, _tool


def pipeline_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "orchestrator.healthcheck",
            "Run the owner-local Orchestrator healthcheck through orchestrator.orchestrator_contract. This only reports runtime and startup readiness and does not mutate pipeline state.",
            {},
        ),
        _tool(
            "orchestrator.reset",
            "Reset the Orchestrator-owned error bundle/run-history for the saved active context by delegating to orchestrator.orchestrator_contract action reset. This does not reset corpus databases, runtime settings, credentials, or MCP support state.",
            {},
        ),
        _tool(
            "inspect_active_workspace_status",
            "Compact operational status for the active workspace. Use this when the user asks what is going on, whether the pipeline is ready, or what the next pipeline tool should be. Returns active workspace paths, Input file count/preview, latest MCP-started run summary, and one next_action. Do not use governance introspection tools for this.",
            {
                "max_input_preview": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 5,
                    "description": "Maximum number of Input filenames to include. The handler caps this at 20.",
                },
            },
        ),
        _tool(
            "inspect_current_environment_status",
            "Canonical read-only current environment status. Use through the Semantic Runtime Kernel when the user asks whether the active workspace, database, input folder, or current pipeline environment exists. Returns stable top-level fields such as database_present, database_path, workspace_present, source_of_truth, input_file_count, latest_run_status, and next_safe_action.",
            {
                "max_input_preview": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 5,
                    "description": "Maximum number of Input filenames to include. The handler caps this at 20.",
                },
            },
        ),
        _tool(
            "run_active_pipeline",
            "Start processing source files from the currently registered Input folder into the active database. Use this when the user says to start/continue processing after files were placed in Input. It loads the Orchestrator's saved active context, checks the Input folder, then runs the pipeline synchronously and returns the run summary. Use mode=batch for all pending files unless the user explicitly asks for only one file.",
            {
                "mode": {
                    "type": "string",
                    "enum": ["batch", "single", "saved"],
                    "default": "batch",
                    "description": "batch processes all pending Input files; single processes the first pending file; saved uses the Orchestrator's saved mode.",
                },
                "require_input_files": {
                    "type": "boolean",
                    "default": True,
                    "description": "When true, do not start a run if the registered Input folder is empty.",
                },
                "max_input_preview": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 20,
                    "description": "Maximum number of Input filenames to echo back before the run.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 3600,
                    "description": "Maximum wall-clock time for the synchronous Orchestrator run.",
                },
            },
        ),
        _tool(
            "start_active_pipeline_run",
            "Start processing source files from the currently registered Input folder in the background and return immediately with a run_id. Use this instead of run_active_pipeline for normal chat UX, because real processing can take a while. Then use inspect_active_pipeline_run to show live status, log tail, and final result.",
            {
                "mode": {
                    "type": "string",
                    "enum": ["batch", "single", "saved"],
                    "default": "batch",
                    "description": "batch processes all pending Input files; single processes the first pending file; saved uses the Orchestrator's saved mode.",
                },
                "require_input_files": {"type": "boolean", "default": True},
                "max_input_preview": {"type": "integer", "minimum": 1, "default": 20},
            },
        ),
        _tool(
            "inspect_active_pipeline_run",
            "Inspect the latest or selected background pipeline run. Returns running/completed/failed status, elapsed time, active workspace, Input preview, live pipeline stage snapshot, pipeline-state summary, recent run log lines, and final run result when available. If run_phase is preflight_failed, the Orchestrator stopped before document processing; do not tell the user that files were processed or that workspace error artifacts should exist.",
            {
                "run_id": {"type": "string", "description": "Optional run_id returned by start_active_pipeline_run. If omitted, the latest run started by MCP is used."},
                "log_tail_lines": {"type": "integer", "minimum": 1, "default": 80},
            },
        ),
        _tool(
            "cancel_active_pipeline_run",
            "Cancel the latest or selected background pipeline run that was started through start_active_pipeline_run. Use this when the user asks to stop or abort processing. It stops the MCP-launched Orchestrator process when the live process is still attached; after an MCP restart it reports the run as interrupted instead of pretending it can cancel it.",
            {
                "run_id": {"type": "string", "description": "Optional run_id returned by start_active_pipeline_run. If omitted, the latest run started by MCP is cancelled."},
                "timeout_seconds": {"type": "integer", "minimum": 1, "default": 10},
            },
        ),
        _tool(
            "preview_active_corpus_source_reimport",
            (
                "Read-only preview for re-importing old source originals that belong to the currently selected corpus DB. "
                "It matches Orchestrator pipeline-state records against active non-archived corpus document content hashes, "
                "then selects only matching files under Documents/originals. It never asks the user to manually sort the Originals folder."
            ),
            {
                "max_preview": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 20,
                    "description": "Maximum selected source entries to include in the preview response. The handler caps this at 100.",
                },
                "conflict_policy": {
                    "type": "string",
                    "enum": ["rename", "skip"],
                    "default": "rename",
                    "description": "How preview should plan Input filename conflicts with different content.",
                },
            },
        ),
        _tool(
            "prepare_active_corpus_source_reimport",
            (
                "Copy old source originals belonging to the currently selected corpus DB back into the active Input folder, "
                "preserving relative paths where possible. This writes a reimport manifest under Documents/logs/reimport and "
                "does not move or delete files from Documents/originals. Use before resetting/switching to an incompatible refined DB, "
                "then run start_active_pipeline_run after the new/empty target DB is active."
            ),
            {
                "user_confirmed": {
                    "type": "boolean",
                    "description": "Must be true after the user confirms that old source documents should be queued for reimport.",
                },
                "conflict_policy": {
                    "type": "string",
                    "enum": ["rename", "skip"],
                    "default": "rename",
                    "description": "rename creates deterministic reimport filenames; skip leaves conflicting Input files untouched.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional cap for the number of source files copied into Input in this preparation step.",
                },
                "max_preview": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 20,
                    "description": "Maximum result entries to echo back. The handler caps this at 100.",
                },
            },
            required=("user_confirmed",),
        ),
    ]
