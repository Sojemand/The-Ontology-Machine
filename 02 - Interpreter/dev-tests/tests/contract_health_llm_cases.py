from __future__ import annotations

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.orchestrator_contract import _generate_llm, _healthcheck
from llm_interpreter.providers import (
    AnthropicProvider,
    GoogleProvider,
    OpenAIChatProvider,
    OpenAIProvider,
    ProviderError,
    create_provider,
)


EXPECTED_PROVIDER_SURFACES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "xai": OpenAIProvider,
    "openrouter": OpenAIChatProvider,
    "groq": OpenAIProvider,
    "together": OpenAIChatProvider,
    "fireworks": OpenAIChatProvider,
    "mistral": OpenAIChatProvider,
    "deepseek": OpenAIChatProvider,
    "sambanova": OpenAIChatProvider,
    "cerebras": OpenAIChatProvider,
    "mammouth": OpenAIChatProvider,
    "lmstudio": OpenAIChatProvider,
    "ollama": OpenAIChatProvider,
    "openai_compat": OpenAIChatProvider,
}

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "xai": "https://api.x.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "sambanova": "https://api.sambanova.ai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "mammouth": "https://api.mammouth.ai/v1",
    "lmstudio": "http://127.0.0.1:1234/v1",
    "ollama": "http://127.0.0.1:11434/v1",
    "openai_compat": "http://127.0.0.1:1234/v1",
}


def test_healthcheck_reports_provider_state(monkeypatch) -> None:
    class DummyProvider:
        def __init__(self) -> None:
            self.calls = 0

        def check_ready(self) -> None:
            self.calls += 1

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig(timeout_seconds=30))
    provider = DummyProvider()
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.create_provider", lambda *args, **kwargs: provider)

    result = _healthcheck({"runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000}})

    assert result["status"] == "ok"
    assert result["healthy"] is True
    assert result["dependencies"][0]["healthy"] is True
    assert provider.calls == 1


def test_generate_llm_uses_orchestrator_runtime_provider(monkeypatch) -> None:
    captured = {}

    class DummyProvider:
        provider_name = "dummy"
        _last_model = "gpt-test"
        _last_response_id = "resp_1"
        _last_usage = {"input_tokens": 1, "output_tokens": 2}

        def generate(self, messages, schema, max_output_tokens, thinking_effort):
            captured["messages"] = messages
            captured["schema"] = schema
            captured["max_output_tokens"] = max_output_tokens
            captured["thinking_effort"] = thinking_effort
            return '{"ok": true}'

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.create_provider", lambda *args, **kwargs: DummyProvider())

    result = _generate_llm(
        {
            "runtime_settings": {"model": "gpt-test", "max_output_tokens": 8000},
            "messages": [{"role": "user", "content": "Return JSON"}],
            "target_schema": {"type": "object"},
            "max_output_tokens": 123,
        }
    )

    llm_response = result["output_refs"]["llm_response"]
    assert result["status"] == "ok"
    assert llm_response["status"] == "complete"
    assert llm_response["output_text"] == '{"ok": true}'
    assert llm_response["usage"] == {"input_tokens": 1, "output_tokens": 2}
    assert captured["max_output_tokens"] == 123
    assert captured["schema"] == {"type": "object"}
    assert captured["thinking_effort"] == "none"


def test_openrouter_provider_defaults_to_chat_completions() -> None:
    provider = create_provider(
        model="openrouter/owl-alpha",
        auth_mode="api_keys",
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-or-test",
    )

    assert isinstance(provider, OpenAIChatProvider)


def test_provider_factory_maps_selectable_providers_to_expected_surfaces() -> None:
    for provider_name, expected_type in EXPECTED_PROVIDER_SURFACES.items():
        provider = create_provider(
            model="model-test",
            auth_mode="api_keys",
            provider_name=provider_name,
            base_url=DEFAULT_BASE_URLS[provider_name],
            api_key="test-key",
        )

        assert isinstance(provider, expected_type), provider_name


def test_generate_llm_converts_provider_auth_error_to_kernel_status(monkeypatch) -> None:
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr(
        "llm_interpreter.orchestrator_contract.create_provider",
        lambda *args, **kwargs: (_ for _ in ()).throw(ProviderError("VISION_PROVIDER_API_KEY nicht gesetzt")),
    )

    result = _generate_llm(
        {
            "runtime_settings": {"model": "gpt-test", "max_output_tokens": 8000},
            "messages": [{"role": "user", "content": "Return JSON"}],
        }
    )

    llm_response = result["output_refs"]["llm_response"]
    assert result["status"] == "ok"
    assert llm_response["status"] == "credentials_missing"
    assert llm_response["output_text"] == ""
