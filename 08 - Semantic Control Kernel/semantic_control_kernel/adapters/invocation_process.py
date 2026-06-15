from __future__ import annotations

import subprocess
from typing import Any

from semantic_control_kernel.adapters.invocation_files import AdapterCallFiles, write_text
from semantic_control_kernel.adapters.invocation_types import AdapterInvocation
from semantic_control_kernel.adapters.owner_process import (
    _communicate_with_progress,
    _minimal_environment,
    _publish_owner_response,
    _select_python_executable,
)
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.process_tree import popen_process_group_kwargs, terminate_process_tree


def execute_owner_process(
    invocation: AdapterInvocation,
    *,
    call_id: str,
    paths: StatePaths,
    files: AdapterCallFiles,
) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    executable = _select_python_executable(invocation.boundary)
    if executable is None:
        diagnostics.append(
            {
                "code": "owner_runtime_missing",
                "message": "No owner runtime Python executable was found.",
                "owner_module_root": str(invocation.boundary.owner_module_root),
            }
        )
        _write_empty_owner_outputs(files)
        return {"status": "owner_error", "owner_status": "missing", "diagnostics": diagnostics}
    return _run_process(invocation, call_id=call_id, paths=paths, files=files, diagnostics=diagnostics, executable=executable)


def _run_process(
    invocation: AdapterInvocation,
    *,
    call_id: str,
    paths: StatePaths,
    files: AdapterCallFiles,
    diagnostics: list[dict[str, Any]],
    executable,
) -> dict[str, Any]:
    command = [
        str(executable),
        "-m",
        invocation.boundary.owner_contract_module,
        "--request",
        str(files.request_path),
        "--response",
        str(files.raw_response_work_path),
    ]
    process = None
    try:
        process = subprocess.Popen(
            command,
            cwd=invocation.boundary.owner_module_root,
            env=_minimal_environment(invocation, call_id),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **popen_process_group_kwargs(),
        )
        stdout, stderr = _communicate_with_progress(process, invocation, diagnostics)
        size_diagnostic = _publish_outputs(files, stdout, stderr)
        if size_diagnostic is not None:
            diagnostics.append(size_diagnostic)
            return {"status": "owner_error", "owner_status": "owner_response_size_limit_exceeded", "diagnostics": diagnostics}
        if process.returncode != 0:
            diagnostics.append({"code": "owner_process_failed", "returncode": process.returncode})
        return {"status": "invalid_owner_response", "owner_status": "missing", "diagnostics": diagnostics}
    except subprocess.TimeoutExpired:
        return _handle_timeout(process, invocation, files, diagnostics)
    except Exception as exc:  # pragma: no cover - defensive boundary conversion
        write_text(files.stdout_path, "")
        write_text(files.stderr_path, str(exc))
        if not files.raw_response_path.exists():
            write_text(files.raw_response_path, "")
        if files.raw_response_work_path.exists():
            files.raw_response_work_path.unlink()
        diagnostics.append({"code": "owner_exception_converted", "exception_type": type(exc).__name__, "message": str(exc)})
        return {"status": "owner_error", "owner_status": "owner_exception_converted", "diagnostics": diagnostics}


def _handle_timeout(process, invocation: AdapterInvocation, files: AdapterCallFiles, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    outcome = terminate_process_tree(process.pid)
    diagnostics.append({"code": "owner_timeout_process_tree_cleanup", **outcome})
    try:
        stdout, stderr = process.communicate(timeout=5)
        diagnostics.append({"code": "owner_timeout_terminated"})
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        diagnostics.append({"code": "owner_timeout_killed"})
    size_diagnostic = _publish_outputs(files, stdout, stderr)
    if size_diagnostic is not None:
        diagnostics.append(size_diagnostic)
    diagnostics.append({"code": "owner_timeout", "timeout_seconds": invocation.boundary.timeout_seconds})
    return {"status": "timeout", "owner_status": "timeout", "diagnostics": diagnostics}


def _publish_outputs(files: AdapterCallFiles, stdout: str | None, stderr: str | None) -> dict[str, Any] | None:
    write_text(files.stdout_path, stdout or "")
    write_text(files.stderr_path, stderr or "")
    return _publish_owner_response(files.raw_response_work_path, files.raw_response_path)


def _write_empty_owner_outputs(files: AdapterCallFiles) -> None:
    write_text(files.stdout_path, "")
    write_text(files.stderr_path, "")
    write_text(files.raw_response_path, "")
