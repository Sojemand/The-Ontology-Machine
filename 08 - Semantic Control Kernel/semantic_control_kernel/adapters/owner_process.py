from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from semantic_control_kernel.repository.atomic_json import atomic_write_text
from semantic_control_kernel.repository.hard_cap_limits import RAW_ADAPTER_CALL_RAW_RESPONSE_FILE_BYTES_HARD_CAP


def _select_python_executable(boundary: Any) -> Path | None:
    if boundary.python_executable is not None and _is_in_module_fake_owner(boundary):
        return boundary.python_executable
    candidates = (
        boundary.owner_module_root / "runtime" / "python" / "Scripts" / "python.exe",
        boundary.owner_module_root / "runtime" / "python" / "python.exe",
        boundary.owner_module_root / "runtime" / "python" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _communicate_with_progress(
    process: subprocess.Popen[str],
    invocation: Any,
    diagnostics: list[dict[str, Any]],
) -> tuple[str, str]:
    timeout_seconds = invocation.boundary.timeout_seconds
    if invocation.progress_callback is None:
        return process.communicate(timeout=timeout_seconds)

    deadline = time.monotonic() + timeout_seconds if timeout_seconds is not None else None
    callback_error_recorded = False
    while True:
        if deadline is None:
            communicate_timeout = 1.0
        else:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, timeout_seconds)
            communicate_timeout = min(1.0, remaining)
        try:
            return process.communicate(timeout=communicate_timeout)
        except subprocess.TimeoutExpired:
            try:
                invocation.progress_callback()
            except Exception as exc:  # pragma: no cover - callback isolation
                if not callback_error_recorded:
                    diagnostics.append(
                        {
                            "code": "progress_callback_failed",
                            "exception_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    )
                    callback_error_recorded = True


def _is_in_module_fake_owner(boundary: Any) -> bool:
    if not boundary.owner_contract_module.startswith("fakes."):
        return False
    normalized_root = boundary.owner_module_root.resolve(strict=False).as_posix().lower()
    return normalized_root.endswith("/dev-tests/fixtures/adapters") or normalized_root.endswith("/dev-tests/fixtures/adapters/fakes")


def _minimal_environment(invocation: Any, call_id: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env["VISION_KERNEL_ADAPTER_CALL_ID"] = call_id
    env["VISION_KERNEL_FUNCTION"] = invocation.kernel_function
    env["VISION_KERNEL_STATE_ROOT"] = str(invocation.state_root)
    if invocation.workflow_run_id:
        env["VISION_KERNEL_WORKFLOW_RUN_ID"] = invocation.workflow_run_id
    target_hash = None
    if invocation.target_identity:
        candidate = invocation.target_identity.get("target_hash") or invocation.target_identity.get("database_path_hash")
        if isinstance(candidate, str):
            target_hash = candidate
    if target_hash:
        env["VISION_KERNEL_TARGET_HASH"] = target_hash
    return env


def _publish_owner_response(work_path: Path, final_path: Path) -> dict[str, Any] | None:
    if not work_path.exists():
        atomic_write_text(final_path, "", temp_dir=work_path.parent)
        return None
    size = work_path.stat().st_size
    if size > RAW_ADAPTER_CALL_RAW_RESPONSE_FILE_BYTES_HARD_CAP:
        payload = {
            "schema_version": "kernel.owner_response_size_limit.v1",
            "status": "error",
            "message": "Owner response exceeded the Kernel adapter-call raw response size limit.",
            "diagnostics": [
                {
                    "code": "owner_response_size_limit_exceeded",
                    "original_size_bytes": size,
                    "size_limit_bytes": RAW_ADAPTER_CALL_RAW_RESPONSE_FILE_BYTES_HARD_CAP,
                }
            ],
        }
        atomic_write_text(final_path, json.dumps(payload, indent=2, sort_keys=True) + "\n", temp_dir=work_path.parent)
        work_path.unlink()
        return payload["diagnostics"][0]
    text = work_path.read_text(encoding="utf-8")
    atomic_write_text(final_path, text, temp_dir=work_path.parent)
    if work_path.exists():
        work_path.unlink()
    return None
