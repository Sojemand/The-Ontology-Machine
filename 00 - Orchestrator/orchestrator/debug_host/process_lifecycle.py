"""Bounded process cleanup for debug-host module steps."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from . import polling

CANCEL_GRACE_SECONDS = 2.0
KILL_GRACE_SECONDS = 2.0


def stop_session_process(session: Any, *, reason: str) -> None:
    handle = session.process_handle
    if handle is None:
        return
    process = handle.process
    try:
        if process.poll() is not None:
            session.process_handle = None
            return
        polling.append_log(session.run_log_path, f"[CANCEL] {reason}; stopping pid={getattr(process, 'pid', '')}")
        process.terminate()
        process.wait(timeout=CANCEL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        _kill_process_tree(process)
    except Exception as exc:
        polling.append_log(session.run_log_path, f"[WARN] {reason}; process stop failed: {exc}")
    finally:
        if _process_has_exited(process):
            session.process_handle = None


def _kill_process_tree(process: Any) -> None:
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            process.kill()
        process.wait(timeout=KILL_GRACE_SECONDS)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _process_has_exited(process: Any) -> bool:
    try:
        return process.poll() is not None
    except Exception:
        return False
