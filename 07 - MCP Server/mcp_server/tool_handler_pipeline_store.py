from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .atomic_io import atomic_json_write
from .contract_client import module_spec
from .tool_handler_runtime_state import PIPELINE_RUN_LOG_TAIL_LINES, _PIPELINE_RUN_PROCESSES, _REAL_POPEN_TYPE

def _state_dir() -> Path:
    path = Path(__file__).resolve().parents[1] / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pipeline_runs_dir() -> Path:
    path = _state_dir() / "pipeline_runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pipeline_run_dir(run_id: str) -> Path | None:
    runs_dir = _pipeline_runs_dir()
    if not runs_dir.exists():
        return None
    if run_id:
        candidate = runs_dir / Path(run_id).name
        return candidate if candidate.exists() and candidate.is_dir() else None
    candidates = sorted(
        (path for path in runs_dir.iterdir() if path.is_dir()),
        key=lambda path: (path / "run.json").stat().st_mtime if (path / "run.json").exists() else path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    atomic_json_write(path, payload, indent=2)


def _elapsed_seconds(metadata: dict[str, Any]) -> float:
    started = metadata.get("started_epoch")
    try:
        return round(max(time.time() - float(started), 0.0), 3)
    except (TypeError, ValueError):
        return 0.0


def _latest_orchestrator_run_log(started_epoch: float) -> Path | None:
    runs_root = module_spec("orchestrator").root / "state" / "pipeline" / "runs"
    if not runs_root.exists():
        return None
    logs = sorted(runs_root.rglob("run.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in logs:
        try:
            if not started_epoch or path.stat().st_mtime >= started_epoch - 2:
                return path
        except OSError:
            continue
    return logs[0] if logs else None


def _tail_text(path: Path, lines: int) -> list[str]:
    try:
        values = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    return values[-max(lines, 1):]


def _terminate_pipeline_process(process: subprocess.Popen, *, timeout_seconds: int) -> dict[str, Any]:
    pid = getattr(process, "pid", None)
    used_taskkill = False
    if os.name == "nt" and isinstance(process, _REAL_POPEN_TYPE) and pid:
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            try:
                process.wait(timeout=2)
            except Exception:
                pass
            used_taskkill = True
            return {
                "termination": "taskkill",
                "return_code": process.poll(),
                "kill_return_code": completed.returncode,
                "kill_stdout": (completed.stdout or "").strip()[-1000:],
                "kill_stderr": (completed.stderr or "").strip()[-1000:],
            }
        except Exception:
            used_taskkill = False
    try:
        process.terminate()
        if hasattr(process, "wait"):
            process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        if hasattr(process, "wait"):
            process.wait(timeout=5)
    except Exception:
        if hasattr(process, "kill"):
            try:
                process.kill()
            except Exception:
                pass
    return {"termination": "terminate", "return_code": process.poll(), "used_taskkill": used_taskkill}


def _mark_pipeline_snapshot_cancelled(snapshot_path: Path) -> None:
    snapshot = _read_json_file(snapshot_path) if snapshot_path.exists() else {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    snapshot["is_running"] = False
    snapshot["aborted"] = True
    _write_json_file(snapshot_path, snapshot)

__all__ = [name for name in globals() if not name.startswith("__")]
