from __future__ import annotations

import json
from types import SimpleNamespace

from orchestrator.debug_host import workflow
from orchestrator.debug_host.types import DebugProcessHandle
from orchestrator.models import RuntimeSettingsState
from tests.debug_host_test_support import write_debug_registry

from cases.debug_host_workflow_interpreter_result_support import write_batch_optimizer_result, write_optimizer_result
from cases.debug_host_workflow_interpreter_support import (
    Process,
    install_interpreter_env_overlay,
    install_launch_capture,
    install_projection_catalog,
    write_working_request,
)


def test_interpreter_plan_launches_debug_run_with_runtime_settings_and_aggregates_outputs(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    launches, _first_process, second_process = install_launch_capture(monkeypatch)
    request_modules: list[str] = []
    install_interpreter_env_overlay(monkeypatch)
    install_projection_catalog(monkeypatch)

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        assert kwargs["projection_catalog"]["catalog_version"] == "sha256:debug"
        request_modules.append(kwargs["module_key"])
        write_working_request(kwargs)
        return {"status": "ok", "request_path": str(kwargs["request_path"])}

    monkeypatch.setattr("orchestrator.debug_host.request_enrichment_steps.request_enrichment.build_working_request", fake_build_working_request)

    modules = SimpleNamespace(_runtime_settings=RuntimeSettingsState())
    session = workflow.start(
        "interpreter",
        "single",
        input_root,
        source_path="docs/invoice.pdf",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"filters": {"format": "pdf"}, "worker_count": 1, "hash_tools": {"use_processed_hashes": True}},
        modules=modules,
    )
    write_optimizer_result(session)

    session = workflow.refresh(session, modules=modules)

    assert request_modules == ["interpreter"]
    assert launches[1]["payload"] == {
        "action": "debug_run",
        "mode": "single",
        "session_root": str(session.session_root),
        "request_path": str(session.output_root / "requests" / "docs" / "invoice.pdf" / "interpreter.request.json"),
        "output_root": str(session.output_root),
        "interpreter_profile": "file",
        "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
    }
    assert launches[1]["env_overlay"] == {
        "INTERPRETER_HOME": str(session.home_path),
        "VISION_OPENAI_AUTH_MODE": "oauth",
    }

    second_process.code = 0
    session.result_path.write_text(
        json.dumps({"status": "ok", "summary": "Interpretation completed", "outputs": {"structured_output": ["outputs/scan.pdf.structured.json"]}}),
        encoding="utf-8",
    )

    session = workflow.refresh(session, modules=modules)

    assert session.active_step is None
    assert session.result is not None
    assert session.result.outputs == {
        "raw_extracts": ["outputs/raw_extracts/docs/invoice.raw.json"],
        "page_assets": ["outputs/page_assets/docs/invoice/page_001.png"],
        "interpreter_request": ["outputs/requests/docs/invoice.pdf/interpreter.request.json"],
        "structured_output": ["outputs/scan.pdf.structured.json"],
    }


def test_interpreter_scan_launches_optimizer_scan_only(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    launches: list[dict[str, object]] = []

    def fake_launch(spec, payload, *, request_path, response_path, env_overlay=None, bootstrap_home=None):  # noqa: ANN001
        launches.append({"spec": spec, "payload": payload, "env_overlay": env_overlay, "bootstrap_home": bootstrap_home})
        return DebugProcessHandle(process=Process(code=None), request_path=request_path, response_path=response_path)

    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch)

    session = workflow.start(
        "interpreter",
        "scan",
        tmp_path / "input",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        modules=SimpleNamespace(_runtime_settings=RuntimeSettingsState()),
    )

    assert session.active_step is not None
    assert session.active_step.label == "optimizer:scan_debug_input"
    assert launches[0]["payload"] == {
        "action": "scan_debug_input",
        "session_root": str(session.session_root),
        "input_root": str(tmp_path / "input"),
        "mode": "scan",
    }


def test_interpreter_batch_launches_request_tree_and_structured_output_dir(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    input_root.mkdir()
    launches, _first_process, second_process = install_launch_capture(monkeypatch)
    request_modules: list[str] = []
    install_interpreter_env_overlay(monkeypatch)
    install_projection_catalog(monkeypatch)

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        assert kwargs["projection_catalog"]["catalog_version"] == "sha256:debug"
        request_modules.append(kwargs["module_key"])
        write_working_request(kwargs, request_value=kwargs["request_path"].as_posix())
        return {"status": "ok", "request_path": str(kwargs["request_path"])}

    monkeypatch.setattr("orchestrator.debug_host.request_enrichment_steps.request_enrichment.build_working_request", fake_build_working_request)

    modules = SimpleNamespace(_runtime_settings=RuntimeSettingsState())
    session = workflow.start("interpreter", "batch", input_root, state_root=tmp_path / "state", registry_path=registry_path, modules=modules)
    write_batch_optimizer_result(session)

    session = workflow.refresh(session, modules=modules)

    assert request_modules == ["interpreter", "interpreter"]
    assert launches[1]["payload"] == {
        "action": "debug_run",
        "mode": "batch",
        "session_root": str(session.session_root),
        "input_root": str(session.output_root / "requests"),
        "output_root": str(session.output_root / "structured_output"),
        "num_workers": 1,
        "interpreter_profile": "file",
        "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
    }

    second_process.code = 0
    session.result_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "summary": "Batch completed",
                "outputs": {
                    "structured_output": [
                        "outputs/structured_output/batch/a.structured.json",
                        "outputs/structured_output/batch/b.structured.json",
                    ]
                },
                "metrics": {"ok": 2, "error": 0, "total": 2, "needs_review": 0},
            }
        ),
        encoding="utf-8",
    )

    session = workflow.refresh(session, modules=modules)

    assert session.result is not None
    assert session.result.outputs == {
        "raw_extracts": ["outputs/raw_extracts/batch/a.raw.json", "outputs/raw_extracts/batch/b.raw.json"],
        "page_assets": ["outputs/page_assets/batch/a/page_001.png", "outputs/page_assets/batch/b/page_001.png"],
        "interpreter_request": [
            "outputs/requests/batch/a/interpreter.request.json",
            "outputs/requests/batch/b/interpreter.request.json",
        ],
        "structured_output": [
            "outputs/structured_output/batch/a.structured.json",
            "outputs/structured_output/batch/b.structured.json",
        ],
    }
