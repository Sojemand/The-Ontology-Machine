from __future__ import annotations

from .tool_handler_deps import *
def inspect_active_pipeline_run(arguments: dict[str, Any]) -> dict[str, Any]:
    run_id = _optional_text(arguments, "run_id")
    log_tail_lines = min(
        _positive_int(arguments.get("log_tail_lines", PIPELINE_RUN_LOG_TAIL_LINES), "log_tail_lines"),
        500,
    )
    run_dir = _pipeline_run_dir(run_id)
    if run_dir is None:
        return {"status": "idle", "message": "Es wurde noch kein Pipeline-Run ueber MCP gestartet."}
    metadata_path = run_dir / "run.json"
    metadata = _read_json_file(metadata_path)
    if not isinstance(metadata, dict):
        metadata = {"run_id": run_dir.name}
    run_id = str(metadata.get("run_id") or run_dir.name)
    response_path = Path(str(metadata.get("response_path") or run_dir / "response.json"))
    snapshot_path = Path(str(metadata.get("snapshot_path") or run_dir / "snapshot.json"))
    stderr_path = Path(str(metadata.get("stderr_path") or run_dir / "stderr.log"))
    process = _PIPELINE_RUN_PROCESSES.get(run_id)
    if process is not None:
        return_code = process.poll()
    else:
        return_code = _safe_int(metadata.get("return_code")) if metadata.get("return_code") is not None else None
    response_payload = _read_json_file(response_path) if response_path.exists() else None
    snapshot_payload = _compact_pipeline_snapshot(_read_json_file(snapshot_path) if snapshot_path.exists() else None)
    zero_document_run = _zero_document_run_summary(response_payload, metadata.get("input_before_run") or {}, snapshot_payload)
    if isinstance(response_payload, dict):
        response_status = str(response_payload.get("status") or "")
        if zero_document_run:
            status = "no_documents_processed"
        elif response_status == "ok":
            status = "completed"
        elif response_status in {"cancelled", "canceled", "aborted"}:
            status = "cancelled"
        else:
            status = "error"
        if process is not None and return_code is not None:
            _PIPELINE_RUN_PROCESSES.pop(run_id, None)
    elif process is not None and return_code is None:
        status = "running"
    elif process is not None:
        status = "failed"
        _PIPELINE_RUN_PROCESSES.pop(run_id, None)
    else:
        status = str(metadata.get("status") or "unknown")
        if status == "running":
            status = "interrupted"
            _mark_run_interrupted(metadata_path, metadata, "MCP Server hat keinen live verwalteten Prozess mehr fuer diesen Run.")
    active_context = metadata.get("active_context") if isinstance(metadata.get("active_context"), dict) else {}
    latest_log = _latest_orchestrator_run_log(float(metadata.get("started_epoch") or 0))
    stderr_tail = _tail_text(stderr_path, 20) if stderr_path.exists() else []
    preflight_failure = _preflight_failure_summary(response_payload, latest_log)
    result = {
        "status": status,
        "run_id": run_id,
        "pid": metadata.get("pid"),
        "return_code": return_code,
        "elapsed_seconds": _elapsed_seconds(metadata),
        "mode": metadata.get("mode", ""),
        "run_phase": "preflight_failed" if preflight_failure else ("no_documents_processed" if zero_document_run else ("processing" if status in {"running", "completed"} else status)),
        "processing_started": preflight_failure is None and zero_document_run is None,
        "active_context": active_context,
        "input_before_run": metadata.get("input_before_run") or {},
        "snapshot": snapshot_payload,
        "pipeline_state": _pipeline_state_summary(active_context),
        "latest_run_log": {
            "path": str(latest_log) if latest_log else "",
            "tail": _tail_text(latest_log, log_tail_lines) if latest_log else [],
        },
        "stderr_tail": stderr_tail,
    }
    if preflight_failure:
        result["preflight_failure"] = preflight_failure
    if zero_document_run:
        result["no_document_processing"] = zero_document_run
        result["message"] = zero_document_run["message"]
    if isinstance(response_payload, dict):
        result["run_result"] = response_payload
    if status == "interrupted":
        result["message"] = "Der Pipeline-Run wurde vor Abschluss aus dem MCP-Prozesskontext verloren. Starte den Run neu oder pruefe die Orchestrator-Logs."
    return result


def cancel_active_pipeline_run(arguments: dict[str, Any]) -> dict[str, Any]:
    run_id = _optional_text(arguments, "run_id")
    timeout_seconds = min(_positive_int(arguments.get("timeout_seconds", 10), "timeout_seconds"), 60)
    run_dir = _pipeline_run_dir(run_id)
    if run_dir is None:
        return {"status": "idle", "run_cancelled": False, "message": "Es wurde noch kein Pipeline-Run ueber MCP gestartet."}
    metadata_path = run_dir / "run.json"
    metadata = _read_json_file(metadata_path)
    if not isinstance(metadata, dict):
        metadata = {"run_id": run_dir.name}
    run_id = str(metadata.get("run_id") or run_dir.name)
    response_path = Path(str(metadata.get("response_path") or run_dir / "response.json"))
    snapshot_path = Path(str(metadata.get("snapshot_path") or run_dir / "snapshot.json"))
    process = _PIPELINE_RUN_PROCESSES.get(run_id)
    return_code = process.poll() if process is not None else None
    if process is None or return_code is not None:
        if process is not None:
            _PIPELINE_RUN_PROCESSES.pop(run_id, None)
        status = "cancelled" if str(metadata.get("status") or "") == "cancelled" else "not_running"
        if status == "not_running" and str(metadata.get("status") or "") == "running":
            status = "interrupted"
            _mark_run_interrupted(metadata_path, metadata, "Cancel konnte keinen live verwalteten MCP-Prozess mehr finden.")
        return {
            "status": status,
            "run_cancelled": False,
            "run_id": run_id,
            "return_code": return_code,
            "message": "Der Pipeline-Run laeuft nicht mehr." if status != "interrupted" else "Der Pipeline-Run ist nach einem MCP-Neustart nicht mehr abbrechbar.",
        }

    termination = _terminate_pipeline_process(process, timeout_seconds=timeout_seconds)
    _PIPELINE_RUN_PROCESSES.pop(run_id, None)
    metadata.update(
        {
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancelled_epoch": time.time(),
            "return_code": termination.get("return_code"),
        }
    )
    _write_json_file(metadata_path, metadata)
    _mark_pipeline_snapshot_cancelled(snapshot_path)
    if not response_path.exists():
        _write_json_file(
            response_path,
            {
                "status": "cancelled",
                "reason": "Pipeline-Run wurde manuell abgebrochen.",
                "run_id": run_id,
            },
        )
    return {
        "status": "cancelled",
        "run_cancelled": True,
        "run_id": run_id,
        "pid": metadata.get("pid"),
        **termination,
        "message": "Pipeline-Run wurde manuell abgebrochen.",
    }


def _mark_run_interrupted(metadata_path: Path, metadata: dict[str, Any], reason: str) -> None:
    metadata.update(
        {
            "status": "interrupted",
            "interrupted_at": datetime.now(timezone.utc).isoformat(),
            "interrupted_epoch": time.time(),
            "interruption_reason": reason,
        }
    )
    _write_json_file(metadata_path, metadata)

__all__ = [name for name in globals() if not name.startswith("__")]
