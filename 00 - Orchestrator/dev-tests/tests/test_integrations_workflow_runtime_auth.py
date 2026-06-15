from __future__ import annotations

from pathlib import Path

from orchestrator.credentials.types import RuntimeCredentialContext
from orchestrator.integrations import EmbeddingStageResult

from .test_integrations_workflow import _modules


def test_interpreter_operation_passes_ephemeral_env_overlay(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "interpreter", with_state_dir=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "orchestrator.credentials.resolve_runtime_credentials",
        lambda *_args, **_kwargs: RuntimeCredentialContext(
            module_key="interpreter",
            auth_mode="oauth",
            ready=True,
            env_overlay={"VISION_OPENAI_AUTH_MODE": "oauth", "VISION_OPENAI_OAUTH_ACCESS_TOKEN": "secret"},
        ),
    )

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        captured["module_key"] = spec.key
        captured["env_overlay"] = env_overlay
        return {"status": "ok", "structured_path": "out.json"}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.interpret_document(tmp_path / "doc.request.json", tmp_path / "doc.structured.json")

    assert captured["module_key"] == "interpreter"
    assert captured["env_overlay"] == {
        "VISION_OPENAI_AUTH_MODE": "oauth",
        "VISION_OPENAI_OAUTH_ACCESS_TOKEN": "secret",
    }


def test_generate_embeddings_returns_disabled_when_embeddings_key_missing(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "corpus_builder", with_state_dir=True)
    monkeypatch.setattr(
        "orchestrator.credentials.resolve_runtime_credentials",
        lambda *_args, **_kwargs: RuntimeCredentialContext(
            module_key="corpus_builder",
            operation="generate_embeddings",
            auth_mode="oauth",
            ready=False,
            warning_only=True,
            message="Embeddings missing",
        ),
    )
    monkeypatch.setattr(
        "orchestrator.integrations.workflow.adapter.invoke_contract",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("invoke_contract should not be called")),
    )

    result = modules.generate_embeddings(tmp_path / "corpus.db")

    assert result == EmbeddingStageResult(status="disabled", count=0, reason="Embeddings missing")


def test_optimizer_vision_extract_passes_optimizer_ocr_env_overlay(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "optimizer", with_state_dir=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "orchestrator.credentials.resolve_runtime_credentials",
        lambda *_args, **_kwargs: RuntimeCredentialContext(
            module_key="optimizer",
            auth_mode="api_keys",
            ready=True,
            env_overlay={"OPTIMIZER_OCR_AUTH_MODE": "api_keys", "OPTIMIZER_OCR_API_KEY": "secret"},
        ),
    )

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["env_overlay"] = env_overlay
        return {
            "status": "success",
            "content_hash": "sha256:test",
            "ingest_id": "ing-1",
            "document_raw_path": "raw.json",
            "page_raw_paths": [],
            "page_asset_paths": [],
        }

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.extract_document_to_targets(
        tmp_path / "scan.png",
        tmp_path / "raw.json",
        tmp_path / "pages",
        optimizer_profile="vision",
    )

    assert captured["module_key"] == "optimizer"
    assert captured["payload"]["optimizer_profile"] == "vision"
    assert captured["env_overlay"] == {
        "OPTIMIZER_OCR_AUTH_MODE": "api_keys",
        "OPTIMIZER_OCR_API_KEY": "secret",
    }


def test_call_operation_converts_parser_failures_into_error_results(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "corpus_builder")
    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", lambda *_args, **_kwargs: {"status": "completed", "count": 1})
    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.parse_embedding_result", lambda _data: (_ for _ in ()).throw(ValueError("bad parse")))

    result = modules.generate_embeddings(tmp_path / "corpus.db")

    assert result == EmbeddingStageResult(status="error", count=0, reason="bad parse")
