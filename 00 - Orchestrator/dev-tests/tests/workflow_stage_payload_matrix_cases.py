from __future__ import annotations

from pathlib import Path

import pytest

from .test_integrations_workflow import _modules


@pytest.mark.parametrize(
    ("module_key", "call", "expected_timeout", "expected_payload", "response_key", "response_value"),
    [
        (
            "optimizer",
            lambda modules, tmp_path: modules.classify_document(tmp_path / "doc.pdf"),
            600,
            lambda tmp_path: {"action": "classify_document", "source_path": str(tmp_path / "doc.pdf")},
            "classification",
            "born_digital_pdf",
        ),
        (
            "optimizer",
            lambda modules, tmp_path: modules.extract_document_to_targets(
                tmp_path / "doc.pdf",
                tmp_path / "optimizer" / "raw_extracts" / "doc.raw.json",
                tmp_path / "optimizer" / "page_images" / "doc.abcd1234",
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
            lambda modules, tmp_path: modules.interpret_document(tmp_path / "doc.request.json", tmp_path / "doc.structured.json"),
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
        (
            "validator",
            lambda modules, tmp_path: modules.validate_document(
                tmp_path / "doc.structured.json",
                tmp_path / "validation" / "doc.vision_validation_report.json",
            ),
            600,
            lambda tmp_path: {
                "action": "validate_document",
                "structured_path": str(tmp_path / "doc.structured.json"),
                "validation_output_path": str(tmp_path / "validation" / "doc.vision_validation_report.json"),
            },
            "report_path",
            "report.json",
        ),
        (
            "normalizer",
            lambda modules, tmp_path: modules.normalize_document(
                tmp_path / "doc.structured.json",
                tmp_path / "normalized" / "doc.structured.normalized.json",
            ),
            1800,
            lambda tmp_path: {
                "action": "normalize_document",
                "structured_path": str(tmp_path / "doc.structured.json"),
                "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            },
            "output_path",
            "normalized.json",
        ),
        (
            "corpus_builder",
            lambda modules, tmp_path: modules.load_document(
                tmp_path / "doc.structured.json",
                tmp_path / "doc.vision_validation_report.json",
                tmp_path / "doc.structured.normalized.json",
                tmp_path / "corpus.db",
            ),
            600,
            lambda tmp_path: {
                "action": "load_document",
                "structured_path": str(tmp_path / "doc.structured.json"),
                "validation_path": str(tmp_path / "doc.vision_validation_report.json"),
                "normalized_path": str(tmp_path / "doc.structured.normalized.json"),
                "corpus_db_path": str(tmp_path / "corpus.db"),
            },
            "status",
            "loaded",
        ),
        (
            "corpus_builder",
            lambda modules, tmp_path: modules.activate_semantic_release(tmp_path / "release.json", tmp_path / "corpus.db"),
            600,
            lambda tmp_path: {
                "action": "activate_semantic_release",
                "release_path": str(tmp_path / "release.json"),
                "corpus_db_path": str(tmp_path / "corpus.db"),
            },
            "status",
            "applied",
        ),
        (
            "corpus_builder",
            lambda modules, tmp_path: modules.generate_embeddings(tmp_path / "corpus.db"),
            1800,
            lambda tmp_path: {
                "action": "generate_embeddings",
                "corpus_db_path": str(tmp_path / "corpus.db"),
                "runtime_settings": {"model": "text-embedding-3-small"},
            },
            "status",
            "completed",
        ),
    ],
)
def test_stage_operations_forward_expected_payloads(
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
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["env_overlay"] = env_overlay
        return {response_key: response_value, "status": "ok" if response_key != "status" else response_value}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    call(modules, tmp_path)

    assert captured["module_key"] == module_key
    assert captured["payload"] == expected_payload(tmp_path)
    assert captured["timeout"] == expected_timeout
    assert captured["env_overlay"] is None
