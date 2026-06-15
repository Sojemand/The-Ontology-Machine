from __future__ import annotations

import json
from pathlib import Path

from orchestrator.debug_host import workflow
from orchestrator.debug_host.types import (
    DebugDescriptor,
    DebugPlan,
    DebugProcessHandle,
    DebugSession,
    DebugSessionRequest,
    DebugStep,
)


class _RunningProcess:
    pid = 12345

    def __init__(self) -> None:
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout=None):  # noqa: ANN001
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def test_cancel_stops_debug_process_and_marks_snapshot(tmp_path: Path) -> None:
    process = _RunningProcess()
    session = _session(tmp_path, process)

    cancelled = workflow.cancel(session)

    assert process.terminated is True
    assert process.killed is False
    assert cancelled.process_handle is None
    assert cancelled.cancel_path.exists()
    assert json.loads(cancelled.snapshot_path.read_text(encoding="utf-8"))["status"] == "cancelling"


def _session(tmp_path: Path, process: _RunningProcess) -> DebugSession:
    step = DebugStep.module("optimizer", "debug_run")
    request = DebugSessionRequest(
        session_id="dbg_test",
        module_key="optimizer",
        mode="single",
        input_root=tmp_path / "input",
        source_path="invoice.pdf",
        output_root=tmp_path / "session" / "outputs",
        session_root=tmp_path / "session",
    )
    descriptor = DebugDescriptor(
        module_key="optimizer",
        display_name="Optimizer",
        stage_role="Optimizer",
        supports_batch=True,
        supports_single=True,
        supports_scan=True,
        input_source="input",
        output_source="output",
        controls=(),
        artifacts=(),
    )
    session = DebugSession(
        request=request,
        descriptor=descriptor,
        plan=DebugPlan("one-step", (step,)),
        active_step=step,
    )
    session.process_handle = DebugProcessHandle(
        process=process,
        request_path=Path("request.json"),
        response_path=Path("response.json"),
    )
    return session
