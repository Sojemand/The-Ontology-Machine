from __future__ import annotations

import os
import signal
import subprocess
from typing import Any


def popen_process_group_kwargs() -> dict[str, Any]:
    if os.name == "nt":
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        create_new_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        flags = create_no_window | create_new_group
        return {"creationflags": flags} if flags else {}
    return {"start_new_session": True}


def terminate_process_tree(pid: int) -> dict[str, str]:
    if pid == os.getpid():
        return {"status": "failed", "detail": "refuses_to_terminate_current_process"}
    if os.name == "nt":
        kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "timeout": 15,
        }
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if create_no_window:
            kwargs["creationflags"] = create_no_window
        try:
            completed = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], **kwargs)
        except subprocess.TimeoutExpired:
            return {"status": "failed", "detail": "taskkill_timeout"}
        detail = (str(completed.stderr or "") or str(completed.stdout or "")).strip()
        if completed.returncode == 0:
            return {"status": "terminated", "detail": detail}
        if "not found" in detail.lower() or "nicht gefunden" in detail.lower():
            return {"status": "missing", "detail": detail}
        return {"status": "failed", "detail": detail or f"taskkill_returncode={completed.returncode}"}
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return {"status": "missing", "detail": "process_not_found"}
        except OSError as exc:
            return {"status": "failed", "detail": str(exc)}
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return {"status": "missing", "detail": "process_not_found"}
        except OSError as exc:
            return {"status": "failed", "detail": str(exc)}
    return {"status": "terminated", "detail": "sigterm_sent"}
