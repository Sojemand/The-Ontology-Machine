from __future__ import annotations

import json

from orchestrator.debug_host import workflow
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_start_support import ModulesWithRuntimeSettings, fake_launch


def test_start_launches_normalizer_with_runtime_settings_and_no_home_overlay(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_normalizer=True)
    structured_dir = tmp_path / "structured"
    structured_dir.mkdir()
    (structured_dir / "invoice.structured.json").write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "normalizer",
        "batch",
        structured_dir,
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"worker_count": 3},
        modules=ModulesWithRuntimeSettings({"normalizer": {"model": "gpt-5.4-mini", "max_output_tokens": 15000}}),
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    assert payload["action"] == "debug_run"
    assert payload["input_root"] == str(structured_dir)
    assert payload["output_root"] == str(session.output_root)
    assert payload["worker_count"] == 3
    assert payload["runtime_settings"] == {"model": "gpt-5.4-mini", "max_output_tokens": 15000}
    assert captured["env_overlay"] is None


def test_start_launches_corpus_builder_single_with_module_selected_file_input(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_corpus_builder=True)
    normalized_path = tmp_path / "normalized" / "invoice.structured.normalized.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "corpus_builder",
        "single",
        normalized_path.parent,
        source_path=str(normalized_path),
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"persist_page_images_in_db": True},
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    assert payload["action"] == "debug_run"
    assert payload["input_root"] == str(normalized_path.parent)
    assert payload["source_path"] == str(normalized_path)
    assert payload["output_root"] == str(session.output_root)
    assert payload["options"] == {"persist_page_images_in_db": True}
    assert "filters" not in payload
    assert "worker_count" not in payload
    assert captured["env_overlay"] is None


def test_start_launches_corpus_builder_scan_with_module_selected_folder_input(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_corpus_builder=True)
    input_root = tmp_path / "artifacts"
    input_root.mkdir()
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "corpus_builder",
        "scan",
        input_root,
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={},
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    assert payload == {
        "action": "scan_debug_input",
        "session_root": str(session.session_root),
        "input_root": str(input_root),
        "mode": "scan",
    }
    assert captured["env_overlay"] is None
