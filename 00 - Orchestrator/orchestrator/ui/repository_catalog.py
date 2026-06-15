"""Model-catalog policy helpers for Orchestrator runtime settings."""

from __future__ import annotations

from ..models import ProviderEndpointSettings, RuntimeSettingsState, provider_definition, provider_display_names, provider_id_for_display_name

_CATALOG_GROUPS = {
    "interpreter": "llm_shared",
    "normalizer": "llm_shared",
    "optimizer_ocr": "optimizer_ocr",
    "corpus_builder_embeddings": "embeddings",
}


def default_runtime_settings() -> RuntimeSettingsState:
    return RuntimeSettingsState()


def catalog_models_for_section(app, section: str) -> tuple[str, ...]:
    group_name = _CATALOG_GROUPS[section]
    provider_settings = _provider_settings_for_section(app, section)
    effective_state = getattr(app, "_model_catalog_effective_state", None)
    models = _catalog_group_models(effective_state, group_name, provider_settings=provider_settings)
    if models:
        return models
    return _catalog_group_models(getattr(app, "_model_catalog_state", None), group_name, provider_settings=provider_settings)


def resolve_catalog_model_for_section(app, section: str, model: str) -> str:
    raw_model = str(model or "").strip()
    if not raw_model:
        return raw_model
    valid_models = catalog_models_for_section(app, section)
    if not valid_models or raw_model in valid_models:
        return raw_model
    matches = [candidate for candidate in valid_models if _models_are_aliases(raw_model, candidate)]
    if len(matches) == 1:
        return matches[0]
    return raw_model


def provider_preset_options(target: str) -> tuple[str, ...]:
    return provider_display_names(target)


def refresh_provider_runtime_labels(app) -> None:
    for target, widgets in getattr(app, "_provider_runtime_widgets", {}).items():
        provider_value = str(getattr(widgets.get("provider"), "get", lambda: "")() or "").strip()
        note = provider_definition(provider_id_for_display_name(provider_value, target=target)).ui_note
        note_widget = widgets.get("note")
        if note_widget is not None and hasattr(note_widget, "configure"):
            note_widget.configure(text=note)


def _catalog_group_models(
    state,
    group_name: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> tuple[str, ...]:
    if state is None or not hasattr(state, "group_for"):
        return ()
    try:
        group = state.group_for(group_name, provider_settings=provider_settings)
    except TypeError:
        group = state.group_for(group_name)
        if provider_settings is not None and not _catalog_group_matches_provider(group, provider_settings):
            return ()
    raw_models = getattr(group, "models", ())
    seen: set[str] = set()
    models: list[str] = []
    for item in raw_models:
        model = str(item or "").strip()
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return tuple(models)


def _provider_settings_for_section(app, section: str) -> ProviderEndpointSettings | None:
    target = _CATALOG_GROUPS.get(section)
    if not target:
        return None
    label = {
        "llm_shared": "LLM Shared Provider",
        "optimizer_ocr": "Optimizer OCR Provider",
    }.get(target, "Embeddings Provider")
    try:
        from .repository_runtime import _read_provider_settings

        return _read_provider_settings(app, target, label=label)
    except Exception:
        return None


def _catalog_group_matches_provider(group, provider_settings: ProviderEndpointSettings) -> bool:
    group_provider_id = str(getattr(group, "provider_id", "") or "").strip()
    group_base_url = str(getattr(group, "base_url", "") or "").strip().rstrip("/")
    if not group_provider_id and not group_base_url:
        return (
            provider_settings.normalized_provider_id() == "openai"
            and provider_settings.normalized_base_url() == "https://api.openai.com/v1"
        )
    return (
        group_provider_id == provider_settings.normalized_provider_id()
        and group_base_url == provider_settings.normalized_base_url()
    )


def _models_are_aliases(left: str, right: str) -> bool:
    return bool(_model_aliases(left) & _model_aliases(right))


def _model_aliases(value: str) -> set[str]:
    raw = str(value or "").strip().lower()
    if not raw:
        return set()
    aliases = {raw}
    if raw.startswith("models/"):
        aliases.add(raw[7:])
    if "/" in raw:
        aliases.add(raw.rsplit("/", 1)[-1])
    return {alias for alias in aliases if alias}


def _provider_preset_for_settings(settings: ProviderEndpointSettings) -> str:
    provider_id = settings.normalized_provider_id()
    base_url = settings.normalized_base_url()
    if provider_id == "openai_compat" and base_url in {"http://127.0.0.1:1234/v1", "http://localhost:1234/v1"}:
        return "LM Studio"
    if provider_id == "openai_compat" and base_url in {"http://127.0.0.1:11434/v1", "http://localhost:11434/v1"}:
        return "Ollama"
    return provider_definition(provider_id).display_name
