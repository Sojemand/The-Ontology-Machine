from __future__ import annotations

import json
from types import SimpleNamespace

from orchestrator.debug_host import workflow
from orchestrator.models import RuntimeSettingsState
from tests.debug_host_test_support import write_debug_registry

from cases.debug_host_workflow_interpreter_result_support import (
    write_optimizer_result_with_page_assets,
    write_optimizer_result_with_page_raw,
    write_optimizer_result_with_trailing_space_raw,
)
from cases.debug_host_workflow_interpreter_support import (
    install_interpreter_env_overlay,
    install_launch_capture,
    install_projection_catalog,
    write_working_request,
)


def test_interpreter_request_enrichment_prefers_document_raw_over_page_raw(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    install_launch_capture(monkeypatch)
    install_interpreter_env_overlay(monkeypatch)
    install_projection_catalog(monkeypatch)
    raw_request_paths: list[str] = []

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        raw_request_paths.append(str(kwargs["raw_path"]))
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
    write_optimizer_result_with_page_raw(session)

    workflow.refresh(session, modules=modules)

    assert len(raw_request_paths) == 1
    assert raw_request_paths[0].endswith("outputs\\raw_extracts\\docs\\invoice.raw.json")


def test_interpreter_request_enrichment_accepts_page_assets_output_key(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    install_launch_capture(monkeypatch)
    install_projection_catalog(monkeypatch)
    working_page_paths: list[str] = []

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        working_page_paths.extend(str(path) for path in kwargs["working_page_paths"])
        write_working_request(kwargs)
        return {"status": "ok", "request_path": str(kwargs["request_path"])}

    monkeypatch.setattr("orchestrator.debug_host.request_enrichment_steps.request_enrichment.build_working_request", fake_build_working_request)

    modules = SimpleNamespace(_runtime_settings=RuntimeSettingsState())
    session = workflow.start("interpreter", "single", input_root, source_path="docs/invoice.pdf", state_root=tmp_path / "state", registry_path=registry_path, modules=modules)
    write_optimizer_result_with_page_assets(session)

    session = workflow.refresh(session, modules=modules)

    assert session.active_step is not None
    assert session.active_step.label == "interpreter:debug_run"
    assert working_page_paths == [str(session.output_root / "page_assets" / "docs" / "invoice" / "page_001.png")]


def test_interpreter_request_enrichment_sanitizes_windows_unsafe_raw_target_suffix(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = input_root / "Auftrag Fa  HAL .msg"
    input_root.mkdir()
    source_path.write_text("msg", encoding="utf-8")
    launches, _first_process, _second_process = install_launch_capture(monkeypatch)
    install_interpreter_env_overlay(monkeypatch)
    install_projection_catalog(monkeypatch)

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        write_working_request(kwargs)
        return {"status": "ok", "request_path": str(kwargs["request_path"])}

    monkeypatch.setattr("orchestrator.debug_host.request_enrichment_steps.request_enrichment.build_working_request", fake_build_working_request)

    modules = SimpleNamespace(_runtime_settings=RuntimeSettingsState())
    session = workflow.start(
        "interpreter",
        "single",
        input_root,
        source_path=str(source_path),
        state_root=tmp_path / "state",
        registry_path=registry_path,
        options={"filters": {"format": "msg"}, "worker_count": 1, "hash_tools": {"use_processed_hashes": True}},
        modules=modules,
    )
    write_optimizer_result_with_trailing_space_raw(session)

    session = workflow.refresh(session, modules=modules)

    assert session.active_step is not None
    assert session.active_step.label == "interpreter:debug_run"
    assert launches[1]["payload"]["request_path"].endswith("outputs\\requests\\Auftrag Fa  HAL\\interpreter.request.json")
    assert (session.output_root / "requests" / "Auftrag Fa  HAL" / "interpreter.request.json").exists()
