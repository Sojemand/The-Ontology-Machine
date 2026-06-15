from __future__ import annotations

from pathlib import Path
from typing import Any

from .tool_handler_corpus_reimport_paths import (
    SUCCESS_DISPOSITIONS,
    active_corpus_hashes,
    blocked_entry,
    count_files,
    hash_file,
    pipeline_state_documents,
    record_belongs_to_active_workspace,
    record_original_source,
    relative_to,
    safe_relative_text,
    target_for_input,
    target_relative_path,
)
from .tool_handler_deps import _active_context_summary, _read_active_orchestrator_ui_state, _validate_active_pipeline_state

_REIMPORT_KERNEL_TOOLS = (
    "database_rebuild_from_artifacts",
    "reset_database",
    "manual_pipeline_run",
)


def build_reimport_plan(*, conflict_policy: str) -> dict[str, Any]:
    ui_state = _read_active_orchestrator_ui_state()
    _validate_active_pipeline_state(ui_state)
    input_root = Path(str(ui_state["input_folder"])).expanduser().resolve()
    artifact_root = Path(str(ui_state["artifact_folder"])).expanduser().resolve()
    corpus_db_path = Path(str(ui_state["selected_corpus_db_path"])).expanduser().resolve()
    originals_root = artifact_root / "Documents" / "originals"
    db_hashes, db_document_count = active_corpus_hashes(corpus_db_path)
    state_path, documents = pipeline_state_documents()
    counters = _empty_counters(len(documents))
    entries = _selected_entries(documents, db_hashes, counters, input_root, artifact_root, originals_root, conflict_policy)
    return {
        "active_context": _active_context_summary(ui_state),
        "pipeline_state_path": str(state_path),
        "originals_root": str(originals_root),
        "originals_total_files": count_files(originals_root),
        "active_db_document_count": db_document_count,
        "active_db_content_hash_count": len(db_hashes),
        "conflict_policy": conflict_policy,
        "counters": counters,
        "entries": entries,
    }


def preview_response(plan: dict[str, Any], *, max_preview: int) -> dict[str, Any]:
    entries = plan["entries"]
    queueable = [item for item in entries if item.get("status") in {"copy", "rename_conflict", "already_in_input"}]
    blocked = [item for item in entries if item.get("status") not in {"copy", "rename_conflict", "already_in_input"}]
    return {
        "status": "ok",
        "question_contract": "corpus_source_reimport",
        "active_context": plan["active_context"],
        "reimport_plan": {
            "pipeline_state_path": plan["pipeline_state_path"],
            "originals_root": plan["originals_root"],
            "originals_total_files": plan["originals_total_files"],
            "active_db_document_count": plan["active_db_document_count"],
            "active_db_content_hash_count": plan["active_db_content_hash_count"],
            "selected_for_reimport": len(queueable),
            "blocked_selected_records": len(blocked),
            "counters": plan["counters"],
            "conflict_policy": plan["conflict_policy"],
        },
        "entries_preview": entries[:max_preview],
        "truncated": len(entries) > max_preview,
        "safe_next_kernel_tools": list(_REIMPORT_KERNEL_TOOLS),
        "user_message_de": preview_message(plan, len(queueable), len(blocked)),
    }


def _selected_entries(
    documents: dict[str, Any],
    db_hashes: set[str],
    counters: dict[str, int],
    input_root: Path,
    artifact_root: Path,
    originals_root: Path,
    conflict_policy: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for record in documents.values():
        if not isinstance(record, dict) or not record_belongs_to_active_workspace(record, input_root, artifact_root):
            continue
        counters["active_workspace_records"] += 1
        content_hash = str(record.get("content_hash") or "").strip()
        if not content_hash or content_hash not in db_hashes:
            counters["skipped_not_in_active_db"] += 1
            continue
        counters["active_db_matching_records"] += 1
        if str(record.get("final_disposition") or "") not in SUCCESS_DISPOSITIONS:
            counters["skipped_non_success_disposition"] += 1
            continue
        entries.append(_entry_for_record(record, content_hash, counters, input_root, artifact_root, originals_root, conflict_policy))
    return entries


def _entry_for_record(
    record: dict[str, Any],
    content_hash: str,
    counters: dict[str, int],
    input_root: Path,
    artifact_root: Path,
    originals_root: Path,
    conflict_policy: str,
) -> dict[str, Any]:
    source_path = record_original_source(record, artifact_root, originals_root)
    if source_path is None:
        counters["missing_original_files"] += 1
        return blocked_entry(record, "missing_original_file", content_hash, input_root)
    if hash_file(source_path) != content_hash:
        counters["hash_mismatch_original_files"] += 1
        return blocked_entry(record, "original_hash_mismatch", content_hash, input_root, source_path)
    target_rel = target_relative_path(record, source_path, originals_root)
    target_path, action = target_for_input(input_root, target_rel, content_hash, conflict_policy_value=conflict_policy)
    counters["selected_records"] += 0 if action == "skip_conflict" else 1
    counters["already_in_input"] += 1 if action == "already_in_input" else 0
    counters["filename_conflicts"] += 1 if action in {"rename_conflict", "skip_conflict"} else 0
    return {
        "status": action,
        "content_hash": content_hash,
        "file_name": str(record.get("file_name") or source_path.name),
        "source_path": str(source_path),
        "target_path": str(target_path),
        "target_relative_path": relative_to(input_root, target_path),
        "original_relative_path": relative_to(originals_root, source_path),
        "pipeline_relative_path": safe_relative_text(record.get("relative_path")) or relative_to(originals_root, source_path),
        "final_disposition": str(record.get("final_disposition") or ""),
    }


def _empty_counters(record_count: int) -> dict[str, int]:
    return {
        "pipeline_state_records": record_count,
        "active_workspace_records": 0,
        "active_db_matching_records": 0,
        "selected_records": 0,
        "skipped_not_in_active_db": 0,
        "skipped_non_success_disposition": 0,
        "missing_original_files": 0,
        "hash_mismatch_original_files": 0,
        "already_in_input": 0,
        "filename_conflicts": 0,
    }


def preview_message(plan: dict[str, Any], queueable: int, blocked: int) -> str:
    if queueable:
        return (
            f"Ich habe {queueable} alte Originaldateien gefunden, die zur aktuell gewaehlten DB gehoeren und fuer den Reimport "
            "gezielt wieder in den Input kopiert werden koennen. Andere Dateien im Originals-Ordner bleiben unberuehrt."
        )
    if plan["active_db_document_count"] == 0:
        return "Die aktuell gewaehlte DB meldet keine aktiven Dokumente; daraus laesst sich kein Reimport alter Originale ableiten."
    if blocked:
        return "Ich habe passende DB-Eintraege gesehen, aber die zugehoerigen Originaldateien fehlen oder passen nicht mehr zum gespeicherten Hash."
    return "Ich habe keine alten Originaldateien gefunden, die zugleich zur aktuell gewaehlten DB und zum aktiven Artefaktbaum gehoeren."


__all__ = [name for name in globals() if not name.startswith("__")]
