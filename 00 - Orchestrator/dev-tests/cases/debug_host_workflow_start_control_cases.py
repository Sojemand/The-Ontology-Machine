from __future__ import annotations

import json

import pytest

from orchestrator.debug_host import workflow
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_start_support import fake_launch, handle_for_request_response


def test_cancel_writes_cancel_request_and_cancelling_snapshot(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path)
    input_root = tmp_path / "input"
    input_root.mkdir()
    monkeypatch.setattr(
        "orchestrator.debug_host.workflow.launcher.launch_process",
        lambda *args, **kwargs: handle_for_request_response(),
    )
    session = workflow.start("optimizer", "scan", input_root, state_root=tmp_path / "state", registry_path=registry_path, options={})

    workflow.cancel(session)

    snapshot = json.loads(session.snapshot_path.read_text(encoding="utf-8"))
    assert session.cancel_path.exists()
    assert snapshot["status"] == "cancelling"


def test_start_rejects_raw_json_as_single_source_for_image_interpreter(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    raw_path = tmp_path / "raw_extracts" / "invoice.pdf.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch({}))

    with pytest.raises(ValueError, match="original file"):
        workflow.start(
            "interpreter",
            "single",
            input_root,
            source_path=str(raw_path),
            state_root=tmp_path / "state",
            registry_path=registry_path,
            options={},
        )


def test_start_accepts_image_source_for_merged_interpreter(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = tmp_path / "scans" / "receipt.jpg"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("image", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "interpreter",
        "single",
        input_root,
        source_path=str(source_path),
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={},
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    assert payload["action"] == "debug_run"
    assert payload["source_path"] == str(source_path)
    assert captured["env_overlay"] == {"OPTIMIZER_HOME": str(session.home_path)}
