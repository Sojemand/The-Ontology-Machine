"""Runtime helpers for process termination in orchestrator workers."""

from __future__ import annotations


def terminate_process_tree(
    pid: int,
    *,
    platform: str,
    windows_collect_process_tree,
    terminate_windows_process,
    os_module,
    signal_module,
) -> None:
    if pid <= 0:
        return
    if platform == "win32":
        for child_pid in reversed(windows_collect_process_tree(pid)):
            terminate_windows_process(child_pid)
        return
    try:
        os_module.killpg(pid, signal_module.SIGKILL)
    except Exception:
        try:
            os_module.kill(pid, signal_module.SIGKILL)
        except Exception:
            pass
