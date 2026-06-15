from __future__ import annotations

from typing import Any

from .tool_handler_corpus_reimport_apply import (
    active_mcp_run_is_running,
    apply_message,
    apply_summary,
    copy_selected_sources,
    write_reimport_manifest,
)
from .tool_handler_corpus_reimport_plan import build_reimport_plan, preview_message, preview_response
from .tool_handler_corpus_reimport_paths import conflict_policy, optional_positive_int, preview_limit
from .tool_handler_deps import ToolFailure, _optional_bool

_REIMPORT_KERNEL_TOOLS = (
    "database_rebuild_from_artifacts",
    "reset_database",
    "manual_pipeline_run",
)


def preview_active_corpus_source_reimport(arguments: dict[str, Any]) -> dict[str, Any]:
    max_preview = preview_limit(arguments)
    plan = build_reimport_plan(conflict_policy=conflict_policy(arguments))
    return preview_response(plan, max_preview=max_preview)


def prepare_active_corpus_source_reimport(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _optional_bool(arguments, "user_confirmed", default=False):
        raise ToolFailure("user_confirmed muss true sein, bevor alte Originaldateien fuer den Reimport vorbereitet werden.")
    if active_mcp_run_is_running():
        raise ToolFailure("Es laeuft bereits ein Pipeline-Lauf. Warte den Lauf ab oder brich ihn ab, bevor Quellen fuer den Reimport vorbereitet werden.")

    max_preview = preview_limit(arguments)
    max_files = optional_positive_int(arguments, "max_files")
    plan = build_reimport_plan(conflict_policy=conflict_policy(arguments))
    applied = copy_selected_sources(plan["entries"], max_files=max_files)
    manifest_path = write_reimport_manifest(plan, applied)
    summary = apply_summary(applied, manifest_path)
    return {
        "status": "ok",
        "question_contract": "corpus_source_reimport",
        "active_context": plan["active_context"],
        "manifest_path": str(manifest_path),
        "reimport_summary": summary,
        "entries_preview": applied[:max_preview],
        "truncated": len(applied) > max_preview,
        "safe_next_kernel_tools": list(_REIMPORT_KERNEL_TOOLS),
        "user_message_de": apply_message(summary),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
