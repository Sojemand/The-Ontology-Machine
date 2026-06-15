from __future__ import annotations

import subprocess as _process_runtime

from .tool_handler_deps import *
def run_active_pipeline(arguments: dict[str, Any]) -> dict[str, Any]:
    mode = _optional_text(arguments, "mode") or "batch"
    if mode not in {"batch", "single", "saved"}:
        raise ToolFailure("mode muss 'batch', 'single' oder 'saved' sein.")
    require_input_files = _optional_bool(arguments, "require_input_files", default=True)
    max_input_preview = _positive_int(arguments.get("max_input_preview", 20), "max_input_preview")
    max_input_preview = min(max_input_preview, PIPELINE_INPUT_PREVIEW_LIMIT)
    timeout_seconds = _positive_int(
        arguments.get("timeout_seconds", DEFAULT_PIPELINE_RUN_TIMEOUT_SECONDS),
        "timeout_seconds",
    )
    timeout_seconds = min(timeout_seconds, PIPELINE_RUN_TIMEOUT_LIMIT_SECONDS)

    ui_state = _read_active_orchestrator_ui_state()
    _validate_active_pipeline_state(ui_state)
    input_preview = _pipeline_input_preview(ui_state["input_folder"], max_items=max_input_preview)
    if require_input_files and input_preview["total_files"] == 0:
        return {
            "status": "no_input_files",
            "run_started": False,
            "message": f"Im aktiven Input Folder liegen keine Dateien: {ui_state['input_folder']}",
            "active_context": _active_context_summary(ui_state),
            "input": input_preview,
        }

    run_state = dict(ui_state)
    if mode != "saved":
        run_state["mode"] = mode
    run = _invoke_product(
        "orchestrator",
        {"action": "run", "ui_state": run_state},
        timeout=timeout_seconds,
    )
    zero_document_run = _zero_document_run_summary(run, input_preview)
    if zero_document_run:
        return {
            "status": "no_documents_processed",
            "run_started": True,
            "run_completed": True,
            "processing_started": False,
            "mode": run_state.get("mode", "batch"),
            "active_context": _active_context_summary(run_state),
            "input_before_run": input_preview,
            "no_document_processing": zero_document_run,
            "message": zero_document_run["message"],
            "run": run,
        }
    return {
        "status": "ok",
        "run_started": True,
        "run_completed": True,
        "mode": run_state.get("mode", "batch"),
        "active_context": _active_context_summary(run_state),
        "input_before_run": input_preview,
        "run": run,
    }


def start_active_pipeline_run(arguments: dict[str, Any]) -> dict[str, Any]:
    mode = _optional_text(arguments, "mode") or "batch"
    if mode not in {"batch", "single", "saved"}:
        raise ToolFailure("mode muss 'batch', 'single' oder 'saved' sein.")
    require_input_files = _optional_bool(arguments, "require_input_files", default=True)
    max_input_preview = min(
        _positive_int(arguments.get("max_input_preview", 20), "max_input_preview"),
        PIPELINE_INPUT_PREVIEW_LIMIT,
    )
    ui_state = _read_active_orchestrator_ui_state()
    _validate_active_pipeline_state(ui_state)
    input_preview = _pipeline_input_preview(ui_state["input_folder"], max_items=max_input_preview)
    if require_input_files and input_preview["total_files"] == 0:
        return {
            "status": "no_input_files",
            "run_started": False,
            "message": f"Im aktiven Input Folder liegen keine Dateien: {ui_state['input_folder']}",
            "active_context": _active_context_summary(ui_state),
            "input": input_preview,
        }

    run_state = dict(ui_state)
    if mode != "saved":
        run_state["mode"] = mode
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    run_dir = _pipeline_runs_dir() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    request_path = run_dir / "request.json"
    response_path = run_dir / "response.json"
    snapshot_path = run_dir / "snapshot.json"
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    metadata_path = run_dir / "run.json"
    payload = {"action": "run", "ui_state": run_state, "snapshot_path": str(snapshot_path)}
    _write_json_file(request_path, payload)
    spec = module_spec("orchestrator")
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            [
                str(spec.python_executable),
                "-m",
                spec.contract_module,
                "--request",
                str(request_path),
                "--response",
                str(response_path),
            ],
            cwd=spec.root,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=_process_runtime.DEVNULL,
            close_fds=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_runtime_env(spec.runtime_dir),
        )
    _PIPELINE_RUN_PROCESSES[run_id] = process
    metadata = {
        "run_id": run_id,
        "status": "running",
        "pid": process.pid,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "started_epoch": time.time(),
        "mode": run_state.get("mode", "batch"),
        "request_path": str(request_path),
        "response_path": str(response_path),
        "snapshot_path": str(snapshot_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "active_context": _active_context_summary(run_state),
        "input_before_run": input_preview,
    }
    _write_json_file(metadata_path, metadata)
    return {
        "status": "started",
        "run_started": True,
        "run_id": run_id,
        "pid": process.pid,
        "mode": run_state.get("mode", "batch"),
        "active_context": metadata["active_context"],
        "input_before_run": input_preview,
        "next_step": "Poll inspect_active_pipeline_run with this run_id for live status and final result.",
    }

__all__ = [name for name in globals() if not name.startswith("__")]
