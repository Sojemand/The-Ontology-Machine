from __future__ import annotations

from pathlib import Path
from typing import Any

from .tool_handler_corpus_reimport_apply import active_mcp_run_is_running
from .tool_handler_corpus_reimport_paths import conflict_policy, hash_file, optional_positive_int, preview_limit, relative_to
from .tool_handler_deps import ToolFailure, _active_context_summary, _optional_bool, _read_active_orchestrator_ui_state, _validate_active_pipeline_state, _write_json_file, datetime, shutil, timezone
from .tool_handler_source_sample_set_paths import source_sample_paths
from .tool_handler_source_sample_set_review import review_source_sample_set_taxonomy_coverage

_REIMPORT_KERNEL_TOOLS = (
    "create_custom_taxonomy_path",
    "create_custom_projection_path",
    "manual_pipeline_run",
)


def prepare_source_samples_for_input(arguments: dict[str, Any]) -> dict[str, Any]:
    if not _optional_bool(arguments, "user_confirmed", default=False):
        raise ToolFailure("user_confirmed muss true sein, bevor neue Sample-Dateien in den Input vorbereitet werden.")
    if active_mcp_run_is_running():
        raise ToolFailure("Es laeuft bereits ein Pipeline-Lauf. Warte den Lauf ab oder brich ihn ab, bevor neue Samples vorbereitet werden.")
    ui_state = _read_active_orchestrator_ui_state()
    _validate_active_pipeline_state(ui_state)
    input_root = Path(str(ui_state["input_folder"])).expanduser().resolve()
    artifact_root = Path(str(ui_state["artifact_folder"])).expanduser().resolve()
    entries = _plan_entries(source_sample_paths(arguments), input_root, conflict_policy(arguments))
    applied = _copy_entries(entries, max_files=optional_positive_int(arguments, "max_files"))
    manifest_path = _write_manifest(artifact_root, _active_context_summary(ui_state), applied, conflict_policy(arguments))
    summary = _summary(applied, manifest_path)
    max_preview = preview_limit(arguments)
    return {
        "status": "ok",
        "question_contract": "document_set_release_refinement",
        "active_context": _active_context_summary(ui_state),
        "manifest_path": str(manifest_path),
        "sample_input_summary": summary,
        "entries_preview": applied[:max_preview],
        "truncated": len(applied) > max_preview,
        "safe_next_kernel_tools": list(_REIMPORT_KERNEL_TOOLS),
        "user_message_de": _message(summary),
    }


def _plan_entries(paths: list[Path], input_root: Path, policy: str) -> list[dict[str, Any]]:
    entries = []
    for source in paths:
        if not source.is_file():
            entries.append(_entry("missing_source_file", source, input_root / source.name, "", input_root))
            continue
        digest = hash_file(source)
        target, status = _target_for_sample(input_root, source.name, digest, policy)
        entries.append(_entry(status, source, target, digest, input_root))
    return entries


def _target_for_sample(input_root: Path, filename: str, digest: str, policy: str) -> tuple[Path, str]:
    target = (input_root / Path(filename).name).resolve()
    if not _within(target, input_root):
        raise ToolFailure(f"Sample-Ziel wuerde ausserhalb des Input-Folders liegen: {target}")
    if not target.exists():
        return target, "copy"
    if hash_file(target) == digest:
        return target, "already_in_input"
    if policy == "skip":
        return target, "skip_conflict"
    return _renamed_sample_target(target, digest, input_root), "rename_conflict"


def _renamed_sample_target(target: Path, digest: str, input_root: Path) -> Path:
    suffix = digest.replace("sha256:", "")[:8] or "sample"
    for index in range(100):
        extra = f".sample-{suffix}" if index == 0 else f".sample-{suffix}-{index}"
        candidate = target.with_name(f"{target.stem}{extra}{target.suffix}").resolve()
        if not _within(candidate, input_root):
            raise ToolFailure(f"Sample-Konfliktziel wuerde ausserhalb des Input-Folders liegen: {candidate}")
        if not candidate.exists() or hash_file(candidate) == digest:
            return candidate
    raise ToolFailure(f"Kein konfliktfreier Sample-Dateiname gefunden fuer: {target}")


def _copy_entries(entries: list[dict[str, Any]], *, max_files: int | None) -> list[dict[str, Any]]:
    copied = 0
    applied = []
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
            _copy_one(entry)
            copied += 1
            result["apply_status"] = "copied"
        applied.append(result)
    return applied


def _copy_one(entry: dict[str, Any]) -> None:
    source = Path(str(entry["source_path"])).expanduser().resolve()
    target = Path(str(entry["target_path"])).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or hash_file(target) != entry.get("content_hash"):
        shutil.copy2(source, target)


def _write_manifest(artifact_root: Path, active_context: dict[str, Any], applied: list[dict[str, Any]], policy: str) -> Path:
    manifest_dir = artifact_root / "Documents" / "logs" / "sample_set_refinement"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = manifest_dir / f"source_sample_set_input_{stamp}.json"
    _write_json_file(path, {
        "artifact_version": "source_sample_set_input_manifest_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Queue user-provided new sample files for the refined archive import.",
        "active_context": active_context,
        "conflict_policy": policy,
        "entries": applied,
    })
    return path


def _summary(applied: list[dict[str, Any]], manifest_path: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for entry in applied:
        status = str(entry.get("apply_status") or entry.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"manifest_path": str(manifest_path), "total_entries": len(applied), "copied": counts.get("copied", 0), "already_queued": counts.get("already_queued", 0), "by_apply_status": counts}


def _entry(status: str, source: Path, target: Path, digest: str, input_root: Path) -> dict[str, Any]:
    return {
        "status": status,
        "content_hash": digest,
        "file_name": source.name,
        "source_path": str(source),
        "target_path": str(target),
        "target_relative_path": relative_to(input_root, target),
    }


def _message(summary: dict[str, Any]) -> str:
    return f"{summary.get('copied', 0)} neue Sample-Dateien wurden in den Input vorbereitet; {summary.get('already_queued', 0)} lagen dort bereits identisch. Alte DB-Originale werden separat ueber den Reimport-Pfad ausgewaehlt."


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


__all__ = [name for name in globals() if not name.startswith("__")]
