from __future__ import annotations

import orchestrator.worker as worker_module
from orchestrator.worker import terminate_process_tree


def test_terminate_process_tree_windows_terminates_children_before_parent(monkeypatch) -> None:
    terminated: list[int] = []

    monkeypatch.setattr(worker_module.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(worker_module, "_windows_collect_process_tree", lambda pid: [pid, pid + 1, pid + 2])
    monkeypatch.setattr(worker_module, "_terminate_windows_process", lambda pid: terminated.append(pid))

    terminate_process_tree(10)

    assert terminated == [12, 11, 10]


def test_terminate_process_tree_ignores_invalid_pid(monkeypatch) -> None:
    called = False

    def fail_if_called(pid: int) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(worker_module, "_terminate_windows_process", fail_if_called, raising=False)

    terminate_process_tree(0)

    assert called is False
