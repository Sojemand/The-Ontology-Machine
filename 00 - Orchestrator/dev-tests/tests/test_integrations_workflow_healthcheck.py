from __future__ import annotations

from pathlib import Path

from orchestrator.credentials.types import RuntimeCredentialContext
from orchestrator.integrations import ModuleHealthStatus

from .test_integrations_workflow import _modules


def test_healthcheck_marks_required_dependency_as_blocking(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "interpreter")

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        assert spec.key == "interpreter"
        assert payload == {
            "action": "healthcheck",
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
        assert timeout == 60
        assert env_overlay is None
        return {
            "status": "error",
            "healthy": False,
            "message": "Provider not ready",
            "dependencies": [{"name": "llm_provider", "kind": "service", "required": True, "healthy": False, "detail": "OPENAI_API_KEY is not set"}],
        }

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    result = modules.healthcheck(module_keys=("interpreter",), scope="pipeline_run")

    assert len(result) == 1
    assert result[0].healthy is False
    assert result[0].blocking_issues() == ["OPENAI_API_KEY is not set"]


def test_interpreter_healthcheck_uses_orchestrator_runtime_settings(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "interpreter")

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        assert spec.key == "interpreter"
        assert payload == {
            "action": "healthcheck",
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
        assert timeout == 60
        assert env_overlay is None
        return {
            "status": "ok",
            "healthy": True,
            "message": "",
            "dependencies": [{"name": "llm_provider", "kind": "service", "required": True, "healthy": True, "detail": "ok"}],
        }

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    result = modules.healthcheck(module_keys=("interpreter",), scope="pipeline_run")

    assert len(result) == 1
    assert result[0].healthy is True

def test_normalizer_healthcheck_uses_orchestrator_runtime_settings(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "normalizer")

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        assert spec.key == "normalizer"
        assert payload == {
            "action": "healthcheck",
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        }
        assert timeout == 60
        assert env_overlay is None
        return {
            "status": "ok",
            "healthy": True,
            "message": "",
            "dependencies": [{"name": "llm_provider", "kind": "service", "required": True, "healthy": True, "detail": "ok"}],
        }

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    result = modules.healthcheck(module_keys=("normalizer",), scope="pipeline_run")

    assert len(result) == 1
    assert result[0].healthy is True


def test_healthcheck_blocks_llm_module_without_contract_call_when_runtime_auth_not_ready(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "interpreter", with_state_dir=True)
    called = {"value": False}
    monkeypatch.setattr(
        "orchestrator.credentials.resolve_runtime_credentials",
        lambda *_args, **_kwargs: RuntimeCredentialContext(
            module_key="interpreter",
            auth_mode="oauth",
            ready=False,
            warning_only=False,
            message="Kein OAuth-Login aktiv",
        ),
    )

    def fake_invoke(*_args, **_kwargs):  # noqa: ANN001
        called["value"] = True
        return {}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    result = modules.healthcheck(module_keys=("interpreter",), scope="pipeline_run")

    assert called["value"] is False
    assert result == [ModuleHealthStatus(key="interpreter", display_name="Interpreter", healthy=False, message="Kein OAuth-Login aktiv")]


def test_healthcheck_treats_empty_response_as_unhealthy(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "interpreter")
    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", lambda *_args, **_kwargs: {})

    result = modules.healthcheck(module_keys=("interpreter",), scope="pipeline_run")

    assert result == [ModuleHealthStatus(key="interpreter", display_name="Interpreter", healthy=False, message="")]


def test_healthcheck_downgrades_missing_embeddings_key_to_optional_warning(tmp_path: Path, monkeypatch) -> None:
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

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        assert spec.key == "corpus_builder"
        assert env_overlay is None
        assert payload == {
            "action": "healthcheck",
            "scope": "pipeline_run",
            "runtime_settings": {"model": "text-embedding-3-small"},
        }
        return {
            "status": "error",
            "healthy": False,
            "message": "embedding provider not ready",
            "dependencies": [
                {"name": "embedding_provider", "kind": "service", "required": True, "healthy": False, "detail": "OPENAI_API_KEY is not set"}
            ],
        }

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    result = modules.healthcheck(module_keys=("corpus_builder",), scope="pipeline_run")

    assert len(result) == 1
    assert result[0].healthy is True
    assert result[0].blocking_issues() == []
    assert result[0].optional_issues() == ["Embeddings missing"]


def test_corpus_builder_healthcheck_forwards_selected_corpus_db_path(tmp_path: Path, monkeypatch) -> None:
    modules = _modules(tmp_path, "corpus_builder")
    selected_db = tmp_path / "Artifact Tree" / "Corpus" / "corpus.db"
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"status": "ok", "healthy": True, "message": "", "dependencies": []}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    result = modules.healthcheck(module_keys=("corpus_builder",), scope="pipeline_run", corpus_db_path=selected_db)

    assert result[0].healthy is True
    assert captured["module_key"] == "corpus_builder"
    assert captured["payload"] == {
        "action": "healthcheck",
        "scope": "pipeline_run",
        "runtime_settings": {"model": "text-embedding-3-small"},
        "corpus_db_path": str(selected_db),
    }
    assert captured["timeout"] == 60

