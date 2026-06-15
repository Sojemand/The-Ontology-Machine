from __future__ import annotations

import json

import pytest

from orchestrator.debug_host import workflow
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_start_support import fake_launch


def test_start_launches_validator_with_module_selected_input_and_options(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_validator=True)
    structured_dir = tmp_path / "structured"
    structured_dir.mkdir()
    captured: dict[str, object] = {}
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch(captured))

    session = workflow.start(
        "validator",
        "batch",
        structured_dir,
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={
            "raw_evidence": {"raw_path": None, "raw_root": str(tmp_path / "raw")},
            "check_toggles": {
                "free_text": True,
                "context_scalars": False,
                "content_fields": True,
                "rows": False,
            },
        },
    )

    payload = json.loads(session.request_path.read_text(encoding="utf-8"))
    assert payload["action"] == "debug_run"
    assert payload["input_root"] == str(structured_dir)
    assert payload["options"]["check_toggles"]["context_scalars"] is False
    assert captured["env_overlay"] == {"VALIDATOR_VISION_HOME": str(session.home_path)}


def test_start_rejects_normalized_json_as_single_input_for_validator(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_validator=True)
    normalized_path = tmp_path / "normalized" / "invoice.structured.normalized.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch({}))

    with pytest.raises(ValueError, match="Validator expects a \\*\\.structured\\.json"):
        workflow.start(
            "validator",
            "single",
            normalized_path.parent,
            source_path=str(normalized_path),
            state_root=tmp_path / "state",
            registry_path=registry_path,
            options={
                "raw_evidence": {},
                "check_toggles": {
                    "free_text": True,
                    "context_scalars": True,
                    "content_fields": True,
                    "rows": True,
                },
            },
        )
