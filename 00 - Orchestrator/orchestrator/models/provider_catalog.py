"""Central provider catalog for orchestrator runtime settings and UI presets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderDefinition:
    provider_id: str
    display_name: str
    family: str
    default_base_url: str
    llm_enabled: bool = True
    embeddings_enabled: bool = False
    api_key_optional: bool = False
    oauth_supported: bool = False
    model_catalog_strategy: str = "openai"
    ui_note: str = ""
    aliases: tuple[str, ...] = ()


_PROVIDER_DEFINITIONS = (
    ProviderDefinition("openai", "OpenAI", "openai_responses", "https://api.openai.com/v1", embeddings_enabled=True, oauth_supported=True, ui_note="Native Responses API plus OpenAI OAuth."),
    ProviderDefinition("anthropic", "Anthropic", "anthropic_messages", "https://api.anthropic.com/v1", model_catalog_strategy="anthropic", ui_note="Native Claude Messages API with tool schema."),
    ProviderDefinition("google", "Google Gemini", "google_gemini", "https://generativelanguage.googleapis.com/v1beta", embeddings_enabled=True, model_catalog_strategy="google", ui_note="Native Gemini generateContent plus JSON Schema."),
    ProviderDefinition("xai", "xAI", "openai_responses", "https://api.x.ai/v1", ui_note="Grok through a Responses-compatible API."),
    ProviderDefinition("openrouter", "OpenRouter", "openai_chat", "https://openrouter.ai/api/v1", embeddings_enabled=True, ui_note="OpenAI-compatible multi-provider gateway using Chat Completions and Embeddings."),
    ProviderDefinition("groq", "Groq", "openai_responses", "https://api.groq.com/openai/v1", ui_note="OpenAI-compatible Responses API on GroqCloud."),
    ProviderDefinition("together", "Together AI", "openai_chat", "https://api.together.xyz/v1", embeddings_enabled=True, ui_note="OpenAI-compatible chat and embedding endpoints."),
    ProviderDefinition("fireworks", "Fireworks AI", "openai_chat", "https://api.fireworks.ai/inference/v1", ui_note="OpenAI-compatible chat endpoints."),
    ProviderDefinition("mistral", "Mistral AI", "openai_chat", "https://api.mistral.ai/v1", ui_note="Mistral inference through a chat-compatible API."),
    ProviderDefinition("deepseek", "DeepSeek", "openai_chat", "https://api.deepseek.com/v1", ui_note="DeepSeek through OpenAI-compatible chat endpoints."),
    ProviderDefinition("sambanova", "SambaNova", "openai_chat", "https://api.sambanova.ai/v1", ui_note="SambaNova Cloud with a chat-compatible API."),
    ProviderDefinition("cerebras", "Cerebras", "openai_chat", "https://api.cerebras.ai/v1", ui_note="Cerebras Inference through a chat-compatible API."),
    ProviderDefinition("mammouth", "Mammouth.ai", "openai_chat", "https://api.mammouth.ai/v1", ui_note="Mammouth speaks OpenAI-compatible chat completions."),
    ProviderDefinition("lmstudio", "LM Studio", "openai_chat", "http://127.0.0.1:1234/v1", embeddings_enabled=True, api_key_optional=True, ui_note="Local LM Studio server. API key optional."),
    ProviderDefinition("ollama", "Ollama", "openai_chat", "http://127.0.0.1:11434/v1", api_key_optional=True, ui_note="Local Ollama OpenAI-compatible endpoint. API key optional."),
    ProviderDefinition("openai_compat", "Custom OpenAI-Compatible", "openai_chat", "http://127.0.0.1:1234/v1", embeddings_enabled=True, api_key_optional=True, ui_note="Free base URL for OpenAI-compatible gateways or local servers."),
)

_PROVIDERS_BY_ID = {definition.provider_id: definition for definition in _PROVIDER_DEFINITIONS}
_ALIASES: dict[str, str] = {
    "": "openai",
    "default": "openai",
    "openai-compatible": "openai_compat",
    "compatible": "openai_compat",
    "custom": "openai_compat",
    "custom openai-compatible": "openai_compat",
    "custom openai compatible": "openai_compat",
    "gemini": "google",
    "google_gemini": "google",
    "google-gemini": "google",
    "lm studio": "lmstudio",
}
for definition in _PROVIDER_DEFINITIONS:
    _ALIASES[definition.provider_id] = definition.provider_id
    _ALIASES[definition.display_name.strip().lower()] = definition.provider_id
    for alias in definition.aliases:
        _ALIASES[alias.strip().lower()] = definition.provider_id

_LLM_PROVIDER_IDS = tuple(
    definition.provider_id for definition in _PROVIDER_DEFINITIONS if definition.llm_enabled
)
_EMBEDDING_PROVIDER_IDS = tuple(
    definition.provider_id for definition in _PROVIDER_DEFINITIONS if definition.embeddings_enabled
)
_OPTIMIZER_OCR_PROVIDER_IDS = tuple(
    definition.provider_id
    for definition in _PROVIDER_DEFINITIONS
    if definition.llm_enabled and definition.family in {"openai_responses", "openai_chat"}
)


def normalize_provider_id(value: object, *, default: str = "openai") -> str:
    raw = str(value or "").strip().lower()
    provider_id = _ALIASES.get(raw, raw or default)
    return provider_id if provider_id in _PROVIDERS_BY_ID else default


def provider_definition(provider_id: object) -> ProviderDefinition:
    return _PROVIDERS_BY_ID[normalize_provider_id(provider_id)]


def provider_ids_for_target(target: str) -> tuple[str, ...]:
    if target == "embeddings":
        return _EMBEDDING_PROVIDER_IDS
    if target == "optimizer_ocr":
        return _OPTIMIZER_OCR_PROVIDER_IDS
    return _LLM_PROVIDER_IDS


def provider_display_names(target: str) -> tuple[str, ...]:
    return tuple(provider_definition(provider_id).display_name for provider_id in provider_ids_for_target(target))


def provider_id_for_display_name(value: object, *, target: str, default: str | None = None) -> str:
    fallback = default or provider_ids_for_target(target)[0]
    provider_id = normalize_provider_id(value, default=fallback)
    return provider_id if provider_id in provider_ids_for_target(target) else fallback


def provider_note(provider_id: object) -> str:
    return provider_definition(provider_id).ui_note
