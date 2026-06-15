from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel.orchestrator_contract import _background_failure_summary
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.surface.background_continuation import launch_interaction_continuation


def test_background_continuation_ref_uses_kernel_state_json_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    written_paths: list[Path] = []
    original_write_json = AtomicJsonStore.write_json

    class FakeProcess:
        pid = 12345

    def fake_popen(*args, **kwargs):
        return FakeProcess()

    def capture_write_json(self, final_path, payload, **kwargs):
        written_paths.append(Path(final_path))
        return original_write_json(self, final_path, payload, **kwargs)

    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation.subprocess.Popen", fake_popen)
    monkeypatch.setattr(AtomicJsonStore, "write_json", capture_write_json)

    ref = launch_interaction_continuation(
        state_paths=paths,
        workflow_run_id="wr_field_ready",
        workflow_tool="manual_pipeline_run",
    )

    assert ref["process_ref"].startswith("debug/background_continuations/wr_field_ready/")
    assert any(path.name.endswith(".ref.json") for path in written_paths)


def test_background_continuation_ref_write_failure_terminates_spawned_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    terminated: list[int] = []

    class FakeProcess:
        pid = 12345

    def fake_popen(*args, **kwargs):
        return FakeProcess()

    def fail_write_json(self, final_path, payload, **kwargs):
        raise OSError("simulated ref persistence failure")

    def fake_terminate(pid: int):
        terminated.append(pid)
        return {"status": "terminated", "detail": "test"}

    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation.subprocess.Popen", fake_popen)
    monkeypatch.setattr(AtomicJsonStore, "write_json", fail_write_json)
    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation._terminate_process_tree", fake_terminate)

    with pytest.raises(OSError):
        launch_interaction_continuation(
            state_paths=paths,
            workflow_run_id="wr_field_ready",
            workflow_tool="manual_pipeline_run",
        )

    assert terminated == [12345]


def test_background_continuation_failure_summary_includes_exception_detail() -> None:
    summary = _background_failure_summary(FileNotFoundError("missing sample artifact"))

    assert "Kernel background continuation failed" in summary
    assert "FileNotFoundError" in summary
    assert "missing sample artifact" in summary
