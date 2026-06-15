from __future__ import annotations

from .tool_handler_deps import *


def inspect_active_workspace_status(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(arguments) - {"max_input_preview"})
    if unknown:
        raise ToolFailure(f"inspect_active_workspace_status kennt diese Argumente nicht: {', '.join(unknown)}")
    max_input_preview = min(_positive_int(arguments.get("max_input_preview", 5), "max_input_preview"), 20)
    state_path = _orchestrator_ui_state_path()
    if not state_path.exists():
        return _workspace_response(
            "no_active_workspace",
            {"state_path": str(state_path), "state_exists": False},
            _empty_input_summary(),
            _latest_workspace_run_summary(),
            "prepare_pipeline_workspace_root",
            "No active Orchestrator workspace context is registered.",
        )

    ui_state = _read_json_file(state_path)
    if not isinstance(ui_state, dict):
        return _workspace_response(
            "needs_attention",
            {"state_path": str(state_path), "state_exists": True, "state_valid": False},
            _empty_input_summary(),
            _latest_workspace_run_summary(),
            "describe_owner_surfaces",
            "The active Orchestrator workspace state is not valid JSON.",
        )

    workspace = _active_workspace_status(ui_state, state_path)
    input_summary = _workspace_input_summary(workspace["input_folder"], max_items=max_input_preview)
    latest_run = _latest_workspace_run_summary()
    status, next_action = _active_workspace_next_action(workspace, input_summary, latest_run)
    return {"status": status, "active_workspace": workspace, "input": input_summary, "latest_run": latest_run, "next_action": next_action}


def inspect_current_environment_status(arguments: dict[str, Any]) -> dict[str, Any]:
    base = inspect_active_workspace_status(arguments)
    workspace = base.get("active_workspace") if isinstance(base.get("active_workspace"), dict) else {}
    path_status = workspace.get("path_status") if isinstance(workspace.get("path_status"), dict) else {}
    input_summary = base.get("input") if isinstance(base.get("input"), dict) else {}
    latest_run = base.get("latest_run") if isinstance(base.get("latest_run"), dict) else {}
    database_path = str(workspace.get("corpus_db_path") or "")
    workspace_path = str(workspace.get("artifact_folder") or "")
    database_present = bool(path_status.get("corpus_db_exists"))
    workspace_present = bool(workspace.get("state_exists")) and bool(path_status.get("artifact_folder_exists"))
    input_folder_present = bool(path_status.get("input_folder_exists"))
    return {
        "status": str(base.get("status") or "unknown"),
        "question_contract": "current_environment_status",
        "source_of_truth": "orchestrator_ui_state",
        "workspace_present": workspace_present,
        "database_present": database_present,
        "database_path": database_path,
        "workspace_path": workspace_path,
        "input_folder_present": input_folder_present,
        "input_file_count": int(input_summary.get("total_files") or 0),
        "latest_run_status": str(latest_run.get("status") or "unknown"),
        "database": {
            "present": database_present,
            "path": database_path,
            "source_field": "active_workspace.corpus_db_path",
        },
        "workspace": {
            "present": workspace_present,
            "path": workspace_path,
            "source_field": "active_workspace.artifact_folder",
        },
        "input": input_summary,
        "latest_run": latest_run,
        "active_workspace": workspace,
        "next_safe_action": base.get("next_action") or {},
    }


def _workspace_response(status: str, workspace: dict[str, Any], input_summary: dict[str, Any], latest_run: dict[str, Any], tool: str, reason: str) -> dict[str, Any]:
    return {"status": status, "active_workspace": workspace, "input": input_summary, "latest_run": latest_run, "next_action": {"tool": tool, "reason": reason}}


def _active_workspace_status(ui_state: dict[str, Any], state_path: Path) -> dict[str, Any]:
    fields = {
        "input_folder": str(ui_state.get("input_folder") or ""),
        "artifact_folder": str(ui_state.get("artifact_folder") or ""),
        "corpus_output_folder": str(ui_state.get("corpus_output_folder") or ""),
        "corpus_db_path": str(ui_state.get("selected_corpus_db_path") or ""),
    }
    missing_fields = [key for key, value in fields.items() if not value.strip()]
    path_status = {
        "input_folder_exists": _is_existing_dir(fields["input_folder"]),
        "artifact_folder_exists": _is_existing_dir(fields["artifact_folder"]),
        "corpus_output_folder_exists": _is_existing_dir(fields["corpus_output_folder"]),
        "corpus_db_exists": _is_existing_file(fields["corpus_db_path"]),
    }
    missing_paths = [key for key, exists in path_status.items() if not exists]
    return {
        "state_path": str(state_path),
        "state_exists": True,
        "state_valid": True,
        **fields,
        "semantic_release_mode": str(ui_state.get("semantic_release_mode") or "database_default"),
        "missing_fields": missing_fields,
        "missing_paths": missing_paths,
        "path_status": path_status,
        "ready": not missing_fields and not missing_paths,
    }


def _workspace_input_summary(input_folder: str, *, max_items: int) -> dict[str, Any]:
    input_path = Path(str(input_folder or "")).expanduser().resolve() if str(input_folder or "").strip() else None
    if input_path is None or not input_path.exists() or not input_path.is_dir():
        summary = _empty_input_summary()
        summary["input_folder"] = str(input_path) if input_path is not None else ""
        return summary
    total_files = 0
    preview_files: list[dict[str, Any]] = []
    for path in input_path.rglob("*"):
        if not path.is_file():
            continue
        total_files += 1
        if len(preview_files) < max_items:
            preview_files.append({"relative_path": _relative_path(path, input_path), "size_bytes": path.stat().st_size})
    return {"input_folder": str(input_path), "exists": True, "total_files": total_files, "preview_count": len(preview_files), "preview_files": preview_files, "truncated": total_files > len(preview_files)}


def _latest_workspace_run_summary() -> dict[str, Any]:
    run_dir = _pipeline_run_dir("")
    if run_dir is None:
        return {"status": "none", "run_id": "", "run_phase": "none"}
    metadata = _read_json_file(run_dir / "run.json")
    metadata = metadata if isinstance(metadata, dict) else {"run_id": run_dir.name}
    run_id = str(metadata.get("run_id") or run_dir.name)
    response_path = Path(str(metadata.get("response_path") or run_dir / "response.json"))
    snapshot_path = Path(str(metadata.get("snapshot_path") or run_dir / "snapshot.json"))
    process = _PIPELINE_RUN_PROCESSES.get(run_id)
    return_code = process.poll() if process is not None else metadata.get("return_code")
    response_payload = _read_json_file(response_path) if response_path.exists() else None
    snapshot_payload = _compact_pipeline_snapshot(_read_json_file(snapshot_path) if snapshot_path.exists() else None)
    status = _brief_run_status(metadata, response_payload, process=process, return_code=return_code)
    return {"status": status, "run_id": run_id, "run_phase": _brief_run_phase(status, response_payload, metadata.get("input_before_run") or {}, snapshot_payload), "mode": str(metadata.get("mode") or ""), "pid": metadata.get("pid"), "return_code": return_code, "elapsed_seconds": _elapsed_seconds(metadata)}


def _brief_run_status(metadata: dict[str, Any], response_payload: Any, *, process: Any, return_code: Any) -> str:
    if process is not None and return_code is None:
        return "running"
    if isinstance(response_payload, dict):
        response_status = str(response_payload.get("status") or "")
        return "completed" if response_status == "ok" else ("cancelled" if response_status in {"cancelled", "canceled", "aborted"} else "error")
    status = str(metadata.get("status") or "")
    return "interrupted" if status == "running" and process is None else (status or "unknown")


def _brief_run_phase(status: str, response_payload: Any, input_before_run: Any, snapshot_payload: dict[str, Any] | None) -> str:
    reason = str(response_payload.get("reason") or response_payload.get("error") or "") if isinstance(response_payload, dict) else ""
    if "Healthcheck fehlgeschlagen" in reason:
        return "preflight_failed"
    if _zero_document_run_summary(response_payload, input_before_run, snapshot_payload):
        return "no_documents_processed"
    return "processing" if status in {"running", "completed"} else status


def _active_workspace_next_action(workspace: dict[str, Any], input_summary: dict[str, Any], latest_run: dict[str, Any]) -> tuple[str, dict[str, str]]:
    if not workspace.get("ready"):
        return "needs_attention", {"tool": "prepare_pipeline_workspace_root", "reason": "The active workspace context is incomplete or points at missing paths."}
    if latest_run.get("status") == "running":
        return "running", {"tool": "inspect_active_pipeline_run", "reason": "A background pipeline run is currently active."}
    if latest_run.get("status") in {"error", "failed", "interrupted"} or latest_run.get("run_phase") in {"preflight_failed", "no_documents_processed"}:
        return "needs_attention", {"tool": "inspect_active_pipeline_run", "reason": "The latest MCP-started pipeline run needs inspection."}
    if int(input_summary.get("total_files") or 0) > 0:
        return "ready_to_run", {"tool": "start_active_pipeline_run", "reason": "The active Input folder contains files and no run is active."}
    return "input_empty", {"tool": "", "reason": "The active workspace is registered, but the Input folder is empty."}


def _empty_input_summary() -> dict[str, Any]:
    return {"input_folder": "", "exists": False, "total_files": 0, "preview_count": 0, "preview_files": [], "truncated": False}


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _is_existing_dir(path_text: str) -> bool:
    return bool(path_text.strip()) and Path(path_text).expanduser().is_dir()


def _is_existing_file(path_text: str) -> bool:
    return bool(path_text.strip()) and Path(path_text).expanduser().is_file()


__all__ = [name for name in globals() if not name.startswith("__")]
