from __future__ import annotations

import json
from pathlib import Path

from .contract_test_support import _run_contract, contract_module

def test_contract_run_returns_summary(monkeypatch, tmp_path: Path) -> None:
    closed: list[bool] = []

    class FakeEngine:
        def run(self, _ui_state):
            return type("RunSummary", (), {"total": 4, "success": 3, "errors": 1, "needs_review": 0, "retries": 2})()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(tmp_path, {"action": "run", "ui_state": {"input_folder": "in"}})

    assert payload == {"status": "ok", "total": 4, "success": 3, "errors": 1, "needs_review": 0, "retries": 2}
    assert closed == [True]

def test_contract_run_writes_snapshot_file(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    snapshot_path = artifact_root / "snapshots" / "pipeline.json"

    class FakeSnapshot:
        def to_dict(self):
            return {
                "total": 2,
                "completed": 1,
                "is_running": True,
                "stage_statuses": {
                    "Optimizer": {
                        "status": "Processing...",
                        "detail": "story.txt",
                        "progress_current": 0,
                        "progress_total": 1,
                        "progress_label": "Requests",
                    }
                },
            }

    class FakeEngine:
        def __init__(self, *, snapshot_callback=None) -> None:
            self.snapshot_callback = snapshot_callback

        def run(self, _ui_state):
            assert self.snapshot_callback is not None
            self.snapshot_callback(FakeSnapshot())
            return type("RunSummary", (), {"total": 2, "success": 1, "errors": 0, "needs_review": 1, "retries": 0})()

        def close(self) -> None:
            pass

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(
        tmp_path,
        {"action": "run", "ui_state": {"artifact_folder": str(artifact_root)}, "snapshot_path": str(snapshot_path)},
    )

    assert payload["status"] == "ok"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["total"] == 2
    assert snapshot["stage_statuses"]["Optimizer"]["detail"] == "story.txt"

def test_snapshot_writer_retries_transient_windows_replace_error(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    snapshot_path = artifact_root / "snapshots" / "pipeline.json"
    real_replace = contract_module.workflow.os.replace
    calls = {"count": 0}

    def flaky_replace(source, target):
        if Path(target) == snapshot_path.resolve() and calls["count"] < 2:
            calls["count"] += 1
            raise PermissionError("[WinError 5] access is denied")
        return real_replace(source, target)

    monkeypatch.setattr(contract_module.workflow.os, "replace", flaky_replace)

    writer = contract_module.workflow._snapshot_file_writer(str(snapshot_path), artifact_root=str(artifact_root))
    writer({"status": "ok"})

    assert calls["count"] == 2
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["status"] == "ok"
    assert snapshot["error_cases_folder"]["exists"] is False

def test_snapshot_writer_reports_live_error_cases_folder(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    error_root = artifact_root / "Error Cases" / "Validator" / "Documents"
    originals_root = error_root / "originals"
    originals_root.mkdir(parents=True)
    (originals_root / "failed.pdf").write_text("source", encoding="utf-8")
    (error_root / "logs").mkdir()
    (error_root / "logs" / "error_bundle.json").write_text("{}", encoding="utf-8")
    snapshot_path = artifact_root / "snapshots" / "pipeline.json"

    writer = contract_module.workflow._snapshot_file_writer(str(snapshot_path), artifact_root=str(artifact_root))
    writer({"status": "running"})

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["error_cases_folder"]["exists"] is True
    assert snapshot["error_cases_folder"]["file_count"] == 1
    assert snapshot["error_cases_folder"]["latest_files"] == ["failed.pdf"]

def test_contract_run_rejects_snapshot_outside_artifact_root(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    snapshot_path = tmp_path / "outside" / "pipeline.json"

    payload = _run_contract(
        tmp_path,
        {"action": "run", "ui_state": {"artifact_folder": str(artifact_root)}, "snapshot_path": str(snapshot_path)},
    )

    assert payload["status"] == "error"
    assert "snapshot_path must stay inside ui_state.artifact_folder" in payload["reason"]
    assert not snapshot_path.exists()
