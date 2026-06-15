from __future__ import annotations

import json
from types import SimpleNamespace

from orchestrator.debug_host import workflow
from orchestrator.debug_host.types import DebugProcessHandle
from orchestrator.models import RuntimeSettingsState
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_interpreter_support import _Process, _write_optimizer_result


def test_interpreter_plan_launches_debug_run_with_runtime_settings_and_aggregates_outputs(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = input_root / "docs" / "invoice.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("pdf", encoding="utf-8")
    launches: list[dict[str, object]] = []
    first_process = _Process(code=0)
    second_process = _Process(code=None)

    def fake_launch(spec, payload, *, request_path, response_path, env_overlay=None, bootstrap_home=None):  # noqa: ANN001
        launches.append({"spec": spec, "payload": payload, "env_overlay": env_overlay, "bootstrap_home": bootstrap_home})
        process = first_process if len(launches) == 1 else second_process
        return DebugProcessHandle(process=process, request_path=request_path, response_path=response_path)

    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch)
    monkeypatch.setattr("orchestrator.debug_host.steps.env_overlay_for", lambda _modules, module_key: {"VISION_OPENAI_AUTH_MODE": "api_keys"} if module_key == "interpreter" else None)
    monkeypatch.setattr(
        "orchestrator.debug_host.request_enrichment_steps.load_normalizer_projection_catalog",
        lambda _modules: {"catalog_version": "sha256:debug", "master_taxonomy_version": "v1", "projections": []},
    )

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        assert kwargs["projection_catalog"]["catalog_version"] == "sha256:debug"
        kwargs["request_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["request_path"].write_text(json.dumps({"request": "ok"}), encoding="utf-8")
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
    _write_optimizer_result(session)

    session = workflow.refresh(session, modules=modules)

    assert launches[1]["payload"] == {
        "action": "debug_run",
        "mode": "single",
        "session_root": str(session.session_root),
        "request_path": str(session.output_root / "requests" / "docs" / "invoice.pdf" / "interpreter.request.json"),
        "output_root": str(session.output_root),
        "interpreter_profile": "vision",
        "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
    }
    assert launches[1]["env_overlay"] == {
        "INTERPRETER_HOME": str(session.home_path),
        "VISION_OPENAI_AUTH_MODE": "api_keys",
    }

    second_process.code = 0
    session.result_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "summary": "Interpretation completed",
                "outputs": {
                    "structured_output": ["outputs/scan.pdf.structured.json"],
                    "llm_output_query_plan": ["outputs/scan.pdf.llm_output.query_plan.json"],
                    "llm_output_pre_merge": ["outputs/scan.pdf.llm_output.pre_merge.json"],
                },
            }
        ),
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
        "llm_output_query_plan": ["outputs/scan.pdf.llm_output.query_plan.json"],
        "llm_output_pre_merge": ["outputs/scan.pdf.llm_output.pre_merge.json"],
    }
