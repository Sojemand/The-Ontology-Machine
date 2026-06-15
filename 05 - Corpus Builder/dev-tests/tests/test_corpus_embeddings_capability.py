from __future__ import annotations

from types import SimpleNamespace

from corpus_builder.database import connect, ensure_schema
from corpus_builder.embeddings import resolve_runtime_capability
from corpus_builder.models.results import EmbeddingRunResult
from corpus_builder.models import EmbeddingRequest, EmbeddingRuntimeSettings
from corpus_builder.orchestrator_contract.types import HealthcheckCommand
from corpus_builder.orchestrator_contract import workflow as contract_workflow
from corpus_builder.services import build_load_bundle, generate_embeddings, load_batch, load_module_config
from tests.fixtures.semantic_context import make_semantic_context


def test_generate_embeddings_without_runtime_capability_returns_disabled(tmp_path, monkeypatch) -> None:
    context = make_semantic_context(tmp_path)
    monkeypatch.setattr(
        "corpus_builder.services.corpus_workflow.resolve_runtime_capability",
        lambda: SimpleNamespace(
            status="unavailable",
            api_key=None,
            reason="Keine Embeddings-API vom Orchestrator bereitgestellt.",
        ),
    )

    result = generate_embeddings(
        context,
        EmbeddingRequest(
            corpus_db_path=str(tmp_path / "output" / "test.corpus.db"),
            runtime_settings=EmbeddingRuntimeSettings(model="test-model"),
        ),
    )

    assert result.status == "disabled"
    assert result.reason == "Keine Embeddings-API vom Orchestrator bereitgestellt."


def test_resolve_runtime_capability_accepts_openai_compatible_base_url_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("VISION_PROVIDER_ID", "openai_compat")
    monkeypatch.setenv("VISION_PROVIDER_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.delenv("VISION_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE_URL", raising=False)

    capability = resolve_runtime_capability()

    assert capability.status == "available"
    assert capability.provider_id == "openai_compat"
    assert capability.base_url == "http://127.0.0.1:1234/v1"
    assert capability.api_key is None


def test_resolve_runtime_capability_preserves_google_family(monkeypatch) -> None:
    monkeypatch.setenv("VISION_PROVIDER_ID", "google")
    monkeypatch.setenv("VISION_PROVIDER_FAMILY", "google_gemini")
    monkeypatch.setenv("VISION_PROVIDER_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    monkeypatch.setenv("VISION_PROVIDER_API_KEY", "google-key")

    capability = resolve_runtime_capability()

    assert capability.status == "available"
    assert capability.provider_id == "google"
    assert capability.provider_family == "google_gemini"


def test_generate_embeddings_accepts_runtime_provider_without_api_key(tmp_path, monkeypatch) -> None:
    context = make_semantic_context(tmp_path)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "corpus_builder.services.corpus_workflow.resolve_runtime_capability",
        lambda: SimpleNamespace(
            status="available",
            api_key=None,
            provider_id="openai_compat",
            base_url="http://127.0.0.1:1234/v1",
            reason="",
        ),
    )
    monkeypatch.setattr(
        "corpus_builder.services.corpus_workflow.embed_pending_result",
        lambda conn, config, runtime_settings, api_key=None: (
            captured.update({"api_key": api_key, "model": runtime_settings.model})
            or EmbeddingRunResult(status="completed", count=2, reason="2 Embeddings erzeugt.")
        ),
    )

    result = generate_embeddings(
        context,
        EmbeddingRequest(
            corpus_db_path=str(tmp_path / "output" / "test.corpus.db"),
            runtime_settings=EmbeddingRuntimeSettings(model="text-embedding-qwen3-embedding-4b"),
        ),
    )

    assert result.status == "completed"
    assert captured == {"api_key": None, "model": "text-embedding-qwen3-embedding-4b"}


def test_contract_healthcheck_sanitizes_provider_detail(monkeypatch) -> None:
    monkeypatch.setattr(
        "corpus_builder.orchestrator_contract.workflow_healthcheck.resolve_runtime_capability",
        lambda: SimpleNamespace(status="available", api_key="injected-secret", base_url="", provider_family="", reason=""),
    )
    monkeypatch.setattr(
        "corpus_builder.orchestrator_contract.workflow_healthcheck.check_api_available",
        lambda _api_key, *, model, base_url=None, provider_family=None: (False, f"HTTP 401 for sk-secret-value while checking {model}"),
    )

    result = contract_workflow.healthcheck(
        HealthcheckCommand(runtime_settings=EmbeddingRuntimeSettings(model="test-model")),
        context=object(),
    )

    assert result["dependencies"][0]["healthy"] is False
    assert "sk-secret-value" not in result["dependencies"][0]["detail"]
