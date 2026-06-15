from __future__ import annotations

import json
from types import SimpleNamespace

from orchestrator.debug_host import workflow
from orchestrator.debug_host.types import DebugProcessHandle
from orchestrator.models import RuntimeSettingsState
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_interpreter_support import _Process, _write_batch_optimizer_result


def test_interpreter_batch_launches_request_tree_and_structured_output_dir(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    input_root.mkdir()
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
        kwargs["request_path"].write_text(json.dumps({"request": kwargs["request_path"].as_posix()}), encoding="utf-8")
        return {"status": "ok", "request_path": str(kwargs["request_path"])}

    monkeypatch.setattr("orchestrator.debug_host.request_enrichment_steps.request_enrichment.build_working_request", fake_build_working_request)

    modules = SimpleNamespace(_runtime_settings=RuntimeSettingsState())
    session = workflow.start(
        "interpreter",
        "batch",
        input_root,
        state_root=tmp_path / "state",
        registry_path=registry_path,
        modules=modules,
    )
    _write_batch_optimizer_result(session)

    session = workflow.refresh(session, modules=modules)

    assert launches[1]["payload"] == {
        "action": "debug_run",
        "mode": "batch",
        "session_root": str(session.session_root),
        "input_root": str(session.output_root / "requests"),
        "output_root": str(session.output_root / "structured_output"),
        "num_workers": 1,
        "interpreter_profile": "vision",
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
                    ],
                    "llm_output_query_plan": [
                        "outputs/structured_output/batch/a.llm_output.query_plan.json",
                        "outputs/structured_output/batch/b.llm_output.query_plan.json",
                    ],
                    "llm_output_pre_merge": [
                        "outputs/structured_output/batch/a.llm_output.pre_merge.json",
                        "outputs/structured_output/batch/b.llm_output.pre_merge.json",
                    ],
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
        "llm_output_query_plan": [
            "outputs/structured_output/batch/a.llm_output.query_plan.json",
            "outputs/structured_output/batch/b.llm_output.query_plan.json",
        ],
        "llm_output_pre_merge": [
            "outputs/structured_output/batch/a.llm_output.pre_merge.json",
            "outputs/structured_output/batch/b.llm_output.pre_merge.json",
        ],
    }
