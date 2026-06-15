from __future__ import annotations

import json

from orchestrator.debug_host import workflow
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_start_support import fake_launch


def test_start_launches_module_step_with_session_artifacts(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "optimizer",
        "single",
        input_root,
        source_path="docs/invoice.pdf",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"filters": {"format": "pdf"}, "worker_count": 1, "hash_tools": {"use_processed_hashes": True}},
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    snapshot = json.loads(session.snapshot_path.read_text(encoding="utf-8"))
    assert payload["action"] == "debug_run"
    assert payload["logical_source_path"] == "docs/invoice.pdf"
    assert snapshot["status"] == "running"
    assert captured["env_overlay"] == {"OPTIMIZER_HOME": str(session.home_path)}


def test_start_launches_optimizer_with_session_home_overlay(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "optimizer",
        "single",
        input_root,
        source_path="docs/invoice.pdf",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"filters": {"format": "pdf"}, "worker_count": 1, "hash_tools": {"use_processed_hashes": True}},
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    assert payload["action"] == "debug_run"
    assert captured["env_overlay"] == {"OPTIMIZER_HOME": str(session.home_path)}


def test_start_launches_optimizer_with_oauth_ocr_overlay(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))
    monkeypatch.setattr(
        "orchestrator.debug_host.steps.env_overlay_for",
        lambda _modules, module_key: {
            "OPTIMIZER_OCR_AUTH_MODE": "oauth",
            "OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN": "secret",
        }
        if module_key == "optimizer"
        else None,
    )

    session = workflow.start(
        "optimizer",
        "single",
        input_root,
        source_path="docs/invoice.pdf",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"filters": {"format": "pdf"}},
        modules=object(),
    )

    assert captured["env_overlay"] == {
        "OPTIMIZER_HOME": str(session.home_path),
        "OPTIMIZER_OCR_AUTH_MODE": "oauth",
        "OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN": "secret",
    }
