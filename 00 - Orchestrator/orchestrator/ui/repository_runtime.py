"""Runtime settings persistence for the Orchestrator UI."""

from __future__ import annotations

from ..models import (
    EmbeddingRuntimeSettings,
    LlmRuntimeSettings,
    OptimizerOcrRuntimeSettings,
    ProviderEndpointSettings,
    RuntimeSettingsState,
    provider_id_for_display_name,
)
from ..state import save_runtime_settings as persist_runtime_settings
from .repository_catalog import _provider_preset_for_settings, catalog_models_for_section, refresh_provider_runtime_labels, resolve_catalog_model_for_section
from .repository_fields import _set_entry_text, _with_suspended_events
from .types import EntryLike


def current_runtime_settings(app) -> RuntimeSettingsState:
    widgets = getattr(app, "_runtime_settings_widgets", {})
    if not widgets:
        state = getattr(app, "_runtime_settings", RuntimeSettingsState())
        state.validate()
        return state
    state = RuntimeSettingsState(
        llm_shared_provider=_read_provider_settings(app, "llm_shared", label="LLM Shared Provider"),
        optimizer_ocr_provider=_read_provider_settings(app, "optimizer_ocr", label="Optimizer OCR Provider"),
        embeddings_provider=_read_provider_settings(app, "embeddings", label="Embeddings Provider"),
        interpreter=_read_llm_runtime_settings(app, widgets, "interpreter", label="Interpreter"),
        normalizer=_read_llm_runtime_settings(app, widgets, "normalizer", label="Normalizer"),
        optimizer_ocr=_read_optimizer_ocr_runtime_settings(app, widgets, "optimizer_ocr", label="Optimizer OCR"),
        corpus_builder_embeddings=_read_embedding_runtime_settings(app, widgets, "corpus_builder_embeddings", label="Corpus Builder Embeddings"),
    )
    state.validate()
    return state


def restore_runtime_settings(app) -> None:
    _with_suspended_events(app, lambda: _write_runtime_settings(app, getattr(app, "_runtime_settings", RuntimeSettingsState())))
    refresh_provider_runtime_labels(app)


def save_runtime_settings(app) -> None:
    app._runtime_settings = current_runtime_settings(app)
    persist_runtime_settings(app._state_dir, app._runtime_settings)


def _write_runtime_settings(app, state: RuntimeSettingsState) -> None:
    _set_provider_entry(app, "llm_shared", "provider", _provider_preset_for_settings(state.llm_shared_provider))
    _set_provider_entry(app, "llm_shared", "base_url", state.llm_shared_provider.base_url)
    _set_provider_entry(app, "optimizer_ocr", "provider", _provider_preset_for_settings(state.optimizer_ocr_provider))
    _set_provider_entry(app, "optimizer_ocr", "base_url", state.optimizer_ocr_provider.base_url)
    _set_provider_entry(app, "embeddings", "provider", _provider_preset_for_settings(state.embeddings_provider))
    _set_provider_entry(app, "embeddings", "base_url", state.embeddings_provider.base_url)
    _set_runtime_entry(app, "interpreter", "model", state.interpreter.model)
    _set_runtime_entry(app, "interpreter", "max_output_tokens", str(state.interpreter.max_output_tokens))
    _set_runtime_entry(app, "normalizer", "model", state.normalizer.model)
    _set_runtime_entry(app, "normalizer", "max_output_tokens", str(state.normalizer.max_output_tokens))
    _set_runtime_entry(app, "optimizer_ocr", "model", state.optimizer_ocr.model)
    _set_runtime_entry(app, "optimizer_ocr", "max_output_tokens", str(state.optimizer_ocr.max_output_tokens))
    _set_runtime_entry(app, "optimizer_ocr", "timeout_seconds", str(state.optimizer_ocr.timeout_seconds))
    _set_runtime_entry(app, "corpus_builder_embeddings", "model", state.corpus_builder_embeddings.model)


def _set_runtime_entry(app, section: str, field_name: str, value: str) -> None:
    widget = getattr(app, "_runtime_settings_widgets", {}).get(section, {}).get(field_name)
    if widget is not None:
        _set_entry_text(widget, value)


def _set_provider_entry(app, target: str, field_name: str, value: str) -> None:
    widget = getattr(app, "_provider_runtime_widgets", {}).get(target, {}).get(field_name)
    if widget is not None:
        _set_entry_text(widget, value)


def _read_provider_settings(app, target: str, *, label: str) -> ProviderEndpointSettings:
    widgets = getattr(app, "_provider_runtime_widgets", {}).get(target, {})
    provider_value = _read_required_text(widgets.get("provider"), label=f"{label}: provider")
    base_url = _read_required_text(widgets.get("base_url"), label=f"{label}: base_url")
    settings = ProviderEndpointSettings(provider_id=provider_id_for_display_name(provider_value, target=target), base_url=base_url)
    settings.validate(label=label)
    return settings


def _read_llm_runtime_settings(app, widgets: dict[str, dict[str, EntryLike]], section: str, *, label: str) -> LlmRuntimeSettings:
    section_widgets = widgets.get(section, {})
    model = _read_catalog_model(app, section, section_widgets, label)
    max_output_tokens = _read_positive_int(section_widgets.get("max_output_tokens"), label=f"{label}: max_output_tokens")
    return LlmRuntimeSettings(model=model, max_output_tokens=max_output_tokens)


def _read_embedding_runtime_settings(app, widgets: dict[str, dict[str, EntryLike]], section: str, *, label: str) -> EmbeddingRuntimeSettings:
    section_widgets = widgets.get(section, {})
    return EmbeddingRuntimeSettings(model=_read_catalog_model(app, section, section_widgets, label))


def _read_optimizer_ocr_runtime_settings(app, widgets: dict[str, dict[str, EntryLike]], section: str, *, label: str) -> OptimizerOcrRuntimeSettings:
    section_widgets = widgets.get(section, {})
    model = _read_catalog_model(app, section, section_widgets, label)
    max_output_tokens = _read_positive_int(section_widgets.get("max_output_tokens"), label=f"{label}: max_output_tokens")
    timeout_seconds = _read_positive_int(section_widgets.get("timeout_seconds"), label=f"{label}: timeout_seconds")
    return OptimizerOcrRuntimeSettings(model=model, max_output_tokens=max_output_tokens, timeout_seconds=timeout_seconds)


def _read_catalog_model(app, section: str, section_widgets: dict[str, EntryLike], label: str) -> str:
    model = resolve_catalog_model_for_section(app, section, _read_required_text(section_widgets.get("model"), label=f"{label}: model"))
    _ensure_catalog_model_allowed(app, section, model, label)
    return model


def _read_required_text(entry: EntryLike | None, *, label: str) -> str:
    if entry is None:
        raise ValueError(f"{label} is missing in the UI.")
    value = entry.get().strip()
    if not value:
        raise ValueError(f"{label} must not be empty.")
    return value


def _read_positive_int(entry: EntryLike | None, *, label: str) -> int:
    value = _read_required_text(entry, label=label)
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a positive integer.") from exc
    if number < 1:
        raise ValueError(f"{label} must be a positive integer.")
    return number


def _ensure_catalog_model_allowed(app, section: str, model: str, label: str) -> None:
    valid_models = catalog_models_for_section(app, section)
    if valid_models and model not in valid_models:
        raise ValueError(f"{label}: model '{model}' is no longer in the current provider catalog.")
