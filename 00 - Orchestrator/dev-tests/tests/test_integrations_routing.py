from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.integrations import ClassificationStageResult

from .test_integrations_workflow import _modules


@pytest.mark.parametrize(
    ("module_key", "call", "expected_timeout", "expected_payload", "response_key", "response_value"),
    [
        (
            "optimizer",
            lambda modules, tmp_path: modules.classify_document(tmp_path / "doc.pdf"),
            600,
            lambda tmp_path: {
                "action": "classify_document",
                "source_path": str(tmp_path / "doc.pdf"),
            },
            "classification",
            "born_digital_pdf",
        ),
        (
            "optimizer",
            lambda modules, tmp_path: modules.extract_document_to_targets(
                tmp_path / "doc.pdf",
                tmp_path / "optimizer" / "raw_extracts" / "doc.raw.json",
                tmp_path / "optimizer" / "page_images" / "doc.abcd1234",
                module_key="optimizer",
                logical_source_path="queue/doc.pdf",
            ),
            1800,
            lambda tmp_path: {
                "action": "extract_document",
                "source_path": str(tmp_path / "doc.pdf"),
                "raw_output_path": str(tmp_path / "optimizer" / "raw_extracts" / "doc.raw.json"),
                "page_assets_dir": str(tmp_path / "optimizer" / "page_images" / "doc.abcd1234"),
                "logical_source_path": "queue/doc.pdf",
            },
            "status",
            "ok",
        ),
        (
            "interpreter",
            lambda modules, tmp_path: modules.interpret_document(
                tmp_path / "doc.request.json",
                tmp_path / "doc.structured.json",
                module_key="interpreter",
            ),
            1800,
            lambda tmp_path: {
                "action": "interpret_document",
                "request_path": str(tmp_path / "doc.request.json"),
                "structured_output_path": str(tmp_path / "doc.structured.json"),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
            },
            "structured_path",
            "out.json",
        ),
    ],
)
def test_route_aware_stage_operations_forward_expected_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_key: str,
    call,
    expected_timeout: int,
    expected_payload,
    response_key: str,
    response_value: str,
) -> None:
    modules = _modules(tmp_path, module_key)
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {response_key: response_value, "status": "ok" if response_key != "status" else response_value}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    call(modules, tmp_path)

    assert captured["module_key"] == module_key
    assert captured["payload"] == expected_payload(tmp_path)
    assert captured["timeout"] == expected_timeout


def test_classify_document_returns_error_result_on_contract_failure(tmp_path, monkeypatch) -> None:
    modules = _modules(tmp_path, "optimizer")
    monkeypatch.setattr(
        "orchestrator.integrations.workflow.adapter.invoke_contract",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("broken classify")),
    )

    result = modules.classify_document(tmp_path / "doc.pdf")

    assert result == ClassificationStageResult(status="error", classification="", reason="", error="broken classify")


def test_optimizer_healthcheck_forwards_required_dependencies(tmp_path, monkeypatch) -> None:
    modules = _modules(tmp_path, "optimizer")
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"status": "ok", "healthy": True, "message": "", "dependencies": []}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.healthcheck(
        module_keys=("optimizer",),
        scope="pipeline_run",
        required_dependencies_by_module={"optimizer": ("renderer-html",)},
    )

    assert captured["module_key"] == "optimizer"
    assert captured["payload"] == {
        "action": "healthcheck",
        "scope": "pipeline_run",
        "required_dependencies": ["renderer-html"],
    }
    assert captured["timeout"] == 60


def test_non_optimizer_healthcheck_does_not_forward_route_dependencies(tmp_path, monkeypatch) -> None:
    modules = _modules(tmp_path, "normalizer")
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"status": "OK", "healthy": True, "message": "", "dependencies": []}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.healthcheck(
        module_keys=("normalizer",),
        scope="pipeline_run",
        required_dependencies_by_module={"normalizer": ("renderer-html",)},
    )

    assert captured["module_key"] == "normalizer"
    assert captured["payload"] == {
        "action": "healthcheck",
        "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
    }
    assert captured["timeout"] == 60

