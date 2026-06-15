from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.services.process_tree import popen_process_group_kwargs, terminate_process_tree


def launch_interaction_continuation(
    *,
    state_paths: StatePaths,
    workflow_run_id: str,
    workflow_tool: str,
) -> dict[str, Any]:
    launch_id = generate_id("background_continuation_id")
    workflow_run_id = require_state_id("workflow_run_id", workflow_run_id)
    log_dir = state_paths.debug_background_continuations_dir / workflow_run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{launch_id}.stdout.json"
    stderr_path = log_dir / f"{launch_id}.stderr.txt"
    command = [
        sys.executable,
        "-m",
        "semantic_control_kernel.orchestrator_contract",
        "continue-after-interaction",
        "--workflow-run-id",
        workflow_run_id,
        "--workflow-tool",
        workflow_tool,
    ]
    env = {**os.environ, "VISION_KERNEL_STATE_ROOT": str(state_paths.state_root)}
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            command,
            cwd=state_paths.module_root,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            text=True,
            close_fds=True,
            env=env,
            **popen_process_group_kwargs(),
        )
    ref = {
        "schema_version": "kernel.background_continuation_ref.v1",
        "launch_id": launch_id,
        "mode": "background_process",
        "pid": process.pid,
        "workflow_run_id": workflow_run_id,
        "workflow_tool": workflow_tool,
        "started_at": utc_iso(),
        "stdout_ref": state_paths.relative_to_state_root(stdout_path),
        "stderr_ref": state_paths.relative_to_state_root(stderr_path),
    }
    ref_path = log_dir / f"{launch_id}.ref.json"
    ref["process_ref"] = state_paths.relative_to_state_root(ref_path)
    try:
        AtomicJsonStore(state_paths, "background_continuations").write_json(ref_path, ref)
    except Exception:
        _terminate_process_tree(process.pid)
        raise
    return ref


def terminate_background_continuations(
    state_paths: StatePaths,
    *,
    workflow_run_ids: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, Any]:
    state_paths.ensure_layout()
    requested = [require_state_id("workflow_run_id", value) for value in workflow_run_ids or [] if str(value)]
    refs = _background_ref_paths(state_paths, requested if workflow_run_ids is not None else None)
    terminated: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    seen_pids: set[int] = set()
    for ref_path in refs:
        ref = _read_ref(ref_path)
        pid = _int_or_none(ref.get("pid"))
        workflow_run_id = str(ref.get("workflow_run_id") or ref_path.parent.name)
        if pid is None or pid <= 0:
            failed.append(_process_result(ref_path, workflow_run_id, pid, "invalid_pid"))
            continue
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        outcome = _terminate_process_tree(pid)
        item = _process_result(ref_path, workflow_run_id, pid, outcome["status"], outcome.get("detail", ""))
        if outcome["status"] == "terminated":
            terminated.append(item)
        elif outcome["status"] == "missing":
            missing.append(item)
        else:
            failed.append(item)
    return {
        "schema_version": "kernel.background_process_termination.v1",
        "requested_workflow_run_ids": requested,
        "ref_count": len(refs),
        "terminated": terminated,
        "missing": missing,
        "failed": failed,
    }


def _background_ref_paths(state_paths: StatePaths, workflow_run_ids: list[str] | None) -> list[Path]:
    base = state_paths.debug_background_continuations_dir
    if workflow_run_ids is None:
        return sorted(base.glob("*/*.ref.json"))
    paths: list[Path] = []
    for workflow_run_id in workflow_run_ids:
        paths.extend(sorted((base / workflow_run_id).glob("*.ref.json")))
    return paths


def _read_ref(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _process_result(
    ref_path: Path,
    workflow_run_id: str,
    pid: int | None,
    status: str,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "workflow_run_id": workflow_run_id,
        "pid": pid,
        "status": status,
        "detail": detail,
        "process_ref": ref_path.as_posix(),
    }


def _terminate_process_tree(pid: int) -> dict[str, str]:
    return terminate_process_tree(pid)


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
