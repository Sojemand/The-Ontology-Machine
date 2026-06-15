from __future__ import annotations

import json
from pathlib import Path

from orchestrator.debug_host import polling
from orchestrator.debug_host.types import DebugProcessHandle


def test_load_snapshot_missing_returns_running_fallback(tmp_path: Path) -> None:
    snapshot = polling.load_snapshot(tmp_path / "missing.json", fallback_stage="Optimizer", fallback_status="running")

    assert snapshot.status == "running"
    assert snapshot.stage == "Optimizer"


def test_load_result_and_log_roundtrip(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    log_path = tmp_path / "run.log"
    result_path.write_text(json.dumps({"status": "ok", "summary": "done", "outputs": {"raw_extracts": ["outputs/raw_extracts/a.raw.json"]}}), encoding="utf-8")
    log_path.write_text("line-1\nline-2\n", encoding="utf-8")

    result = polling.load_result(result_path)

    assert result is not None
    assert result.outputs["raw_extracts"] == ["outputs/raw_extracts/a.raw.json"]
    assert polling.load_log(log_path) == "line-1\nline-2\n"


def test_append_log_is_append_only(tmp_path: Path) -> None:
    log_path = tmp_path / "run.log"

    polling.append_log(log_path, "first")
    polling.append_log(log_path, "second")

    lines = polling.load_log(log_path).splitlines()
    assert lines[0].endswith("first")
    assert lines[1].endswith("second")


def test_process_exit_code_handles_missing_and_finished_processes() -> None:
    class _Process:
        def __init__(self, code):
            self._code = code

        def poll(self):
            return self._code

    handle = DebugProcessHandle(process=_Process(0), request_path=Path("request.json"), response_path=Path("response.json"))

    assert polling.process_exit_code(None) == 0
    assert polling.process_exit_code(handle) == 0
