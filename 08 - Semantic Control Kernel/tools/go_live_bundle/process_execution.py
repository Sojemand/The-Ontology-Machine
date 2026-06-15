from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .command_matrix import CommandSpec
from .paths import PIPELINE_ROOT, _mkdir, _slug
from .scans import _execute_scan_command


def _execute_command_spec(index: int, spec: CommandSpec, bundle_root: Path, run_id: str, log_path: Path) -> dict[str, Any]:
    workdir = PIPELINE_ROOT if spec.working_directory == "." else PIPELINE_ROOT / spec.working_directory
    started = datetime.now(timezone.utc)
    actual_command = _actual_command(spec, workdir)
    if spec.module_key == "scan":
        exit_code, stdout, stderr = _execute_scan_command(spec)
        timed_out = False
    else:
        exit_code, stdout, stderr, timed_out = _run_command_with_file_capture(
            actual_command,
            workdir,
            timeout_seconds=spec.timeout_seconds,
            log_path=log_path,
        )
    duration = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
    result = "pass" if exit_code == 0 else "fail"
    blocker_anchor = "" if result == "pass" else f"command-{index:02d}-{_slug(spec.module_key)}-{_slug(spec.purpose)}"
    record = {
        "sequence_index": index,
        "module_key": spec.module_key,
        "purpose": spec.purpose,
        "command": spec.command,
        "working_directory": spec.working_directory,
        "expected_test_scope": spec.expected_test_scope,
        "produced_evidence_path": f"commands/{log_path.name}",
        "log_path": f"commands/{log_path.name}",
        "exit_code": exit_code,
        "result": result,
        "blocking_issue_anchor": blocker_anchor,
        "duration_seconds": duration,
    }
    log_lines = [
        f"go_live_run_id={run_id}",
        f"command={spec.command}",
        f"actual_invocation={' '.join(actual_command)}",
        f"working_directory={spec.working_directory}",
        f"expected_test_scope={spec.expected_test_scope}",
        f"started_at={started.isoformat().replace('+00:00', 'Z')}",
        f"duration_seconds={duration}",
        f"exit_code={exit_code}",
        f"result={result}",
        f"timed_out={str(timed_out).lower()}",
        "",
        "===== STDOUT =====",
        stdout.rstrip(),
        "",
        "===== STDERR =====",
        stderr.rstrip(),
        "",
    ]
    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    return record


def _run_command_with_file_capture(
    actual_command: list[str],
    workdir: Path,
    *,
    timeout_seconds: int,
    log_path: Path,
) -> tuple[int, str, str, bool]:
    stdout_path = log_path.with_suffix(log_path.suffix + ".stdout.tmp")
    stderr_path = log_path.with_suffix(log_path.suffix + ".stderr.tmp")
    _mkdir(stdout_path.parent)
    stdout_position = 0
    stderr_position = 0
    deadline = time.monotonic() + timeout_seconds
    try:
        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_handle, stderr_path.open(
            "w",
            encoding="utf-8",
            errors="replace",
        ) as stderr_handle:
            process = subprocess.Popen(
                actual_command,
                cwd=workdir,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            while True:
                stdout_position = _pump_capture_output(stdout_path, stdout_position, sys.stdout)
                stderr_position = _pump_capture_output(stderr_path, stderr_position, sys.stderr)
                return_code = process.poll()
                if return_code is not None:
                    exit_code = int(return_code)
                    timed_out = False
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    process.kill()
                    process.wait(timeout=30)
                    exit_code = 124
                    break
                time.sleep(1)
        _pump_capture_output(stdout_path, stdout_position, sys.stdout)
        _pump_capture_output(stderr_path, stderr_position, sys.stderr)
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
        return exit_code, stdout, stderr, timed_out
    finally:
        for capture_path in (stdout_path, stderr_path):
            try:
                capture_path.unlink()
            except OSError:
                pass


def _pump_capture_output(path: Path, offset: int, stream: Any) -> int:
    if not path.exists():
        return offset
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(offset)
        chunk = handle.read()
        next_offset = handle.tell()
    if chunk:
        try:
            stream.write(chunk)
        except UnicodeEncodeError:
            encoding = getattr(stream, "encoding", None) or "utf-8"
            stream.write(chunk.encode(encoding, errors="replace").decode(encoding, errors="replace"))
        stream.flush()
    return next_offset


def _coerce_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _actual_command(spec: CommandSpec, workdir: Path) -> list[str]:
    if spec.module_key == "scan":
        return [sys.executable, "-m", "phase20_internal_scan", spec.purpose]
    if spec.module_key == "frontend" and spec.purpose == "build":
        return [
            str(workdir / "node" / "node.exe"),
            str(workdir / "node_modules" / "vite" / "bin" / "vite.js"),
            "build",
            "--configLoader",
            "runner",
        ]
    if spec.module_key in {"mcp", "orchestrator", "normalizer", "corpus"} and spec.command.startswith(r"dev-tests\run-tests.bat "):
        return _targeted_pytest_command(spec, workdir)
    return ["cmd.exe", "/d", "/c", spec.command]


def _targeted_pytest_command(spec: CommandSpec, workdir: Path) -> list[str]:
    python_exe = _suite_python(workdir)
    test_args = spec.command.split(maxsplit=1)[1].split()
    resolved_args = [_module_local_test_path(name) for name in test_args]
    if spec.module_key == "corpus":
        base_temp = workdir / "dev-tests" / ".pytest-phase20"
        _mkdir(base_temp)
        return [str(python_exe), "-m", "pytest", *resolved_args, "-q", "-m", "not stress", "--basetemp", str(base_temp)]
    return [str(python_exe), "-m", "pytest", *resolved_args, "-q"]


def _module_local_test_path(name: str) -> str:
    normalized = name.replace("/", "\\")
    if normalized.startswith("dev-tests\\tests\\"):
        return normalized
    if normalized.startswith("tests\\"):
        return f"dev-tests\\{normalized}"
    return f"dev-tests\\tests\\{normalized}"


def _suite_python(workdir: Path) -> Path:
    candidates = (
        workdir / "dev-tests" / ".venv" / "python.exe",
        workdir / "dev-tests" / ".venv" / "Scripts" / "python.exe",
        workdir / "dev-tests" / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
