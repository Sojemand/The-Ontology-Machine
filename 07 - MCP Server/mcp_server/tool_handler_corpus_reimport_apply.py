from __future__ import annotations

from pathlib import Path
from typing import Any

from .tool_handler_corpus_reimport_paths import hash_file
from .tool_handler_deps import _PIPELINE_RUN_PROCESSES, _pipeline_run_dir, _read_json_file, _write_json_file, datetime, shutil, timezone


def active_mcp_run_is_running() -> bool:
    run_dir = _pipeline_run_dir("")
    if run_dir is None:
        return False
    metadata = _read_json_file(run_dir / "run.json")
    metadata = metadata if isinstance(metadata, dict) else {}
    run_id = str(metadata.get("run_id") or run_dir.name)
    process = _PIPELINE_RUN_PROCESSES.get(run_id)
    if process is not None and process.poll() is None:
        return True
    return str(metadata.get("status") or "") == "running" and process is not None


def copy_selected_sources(entries: list[dict[str, Any]], *, max_files: int | None) -> list[dict[str, Any]]:
    copied = 0
    applied: list[dict[str, Any]] = []
    for entry in entries:
        result = dict(entry)
        status = str(entry.get("status") or "")
        if status == "already_in_input":
            result["apply_status"] = "already_queued"
        elif status not in {"copy", "rename_conflict"}:
            result["apply_status"] = "skipped"
        elif max_files is not None and copied >= max_files:
            result["apply_status"] = "skipped_max_files"
        else:
            copied += _copy_one_source(entry, result)
        applied.append(result)
    return applied


def _copy_one_source(entry: dict[str, Any], result: dict[str, Any]) -> int:
    source_path = Path(str(entry.get("source_path") or "")).expanduser().resolve()
    target_path = Path(str(entry.get("target_path") or "")).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and hash_file(target_path) == entry.get("content_hash"):
        result["apply_status"] = "already_queued"
        return 0
    shutil.copy2(source_path, target_path)
    result["apply_status"] = "copied"
    return 1


def write_reimport_manifest(plan: dict[str, Any], applied: list[dict[str, Any]]) -> Path:
    artifact_root = Path(str(plan["active_context"]["artifact_folder"])).expanduser().resolve()
    manifest_dir = artifact_root / "Documents" / "logs" / "reimport"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = manifest_dir / f"active_corpus_source_reimport_{stamp}.json"
    _write_json_file(
        manifest_path,
        {
            "artifact_version": "active_corpus_source_reimport_manifest_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "Queue old source originals from the active corpus DB for reimport after release refinement.",
            "active_context": plan["active_context"],
            "pipeline_state_path": plan["pipeline_state_path"],
            "originals_root": plan["originals_root"],
            "active_db_document_count": plan["active_db_document_count"],
            "active_db_content_hash_count": plan["active_db_content_hash_count"],
            "conflict_policy": plan["conflict_policy"],
            "counters": plan["counters"],
            "entries": applied,
        },
    )
    return manifest_path


def apply_summary(applied: list[dict[str, Any]], manifest_path: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for entry in applied:
        status = str(entry.get("apply_status") or entry.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "manifest_path": str(manifest_path),
        "total_entries": len(applied),
        "copied": counts.get("copied", 0),
        "already_queued": counts.get("already_queued", 0),
        "skipped": counts.get("skipped", 0),
        "skipped_max_files": counts.get("skipped_max_files", 0),
        "by_apply_status": counts,
    }


def apply_message(summary: dict[str, Any]) -> str:
    copied = int(summary.get("copied") or 0)
    already = int(summary.get("already_queued") or 0)
    if copied or already:
        return (
            f"{copied} alte Originaldateien wurden in den Input vorbereitet; {already} lagen dort bereits identisch. "
            "Nach Aktivierung oder Neuaufbau der Ziel-DB kann der normale Pipeline-Lauf starten und die neuen Input-Dateien werden mit verarbeitet."
        )
    return "Es wurden keine alten Originaldateien in den Input kopiert; Details stehen im Reimport-Manifest."


__all__ = [name for name in globals() if not name.startswith("__")]
