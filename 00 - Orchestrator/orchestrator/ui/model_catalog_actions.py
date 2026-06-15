"""UI-side workflow for seeded and refreshed model catalogs."""

from __future__ import annotations

import threading

from .. import credentials, model_catalog
from ..model_catalog import ModelCatalogState
from ..models import provider_definition
from . import repository, theme
_GROUP_LABELS = {
    "llm_shared": "LLM Catalog",
    "optimizer_ocr": "Optimizer OCR Catalog",
    "embeddings": "Embedding Catalog",
}


def initialize_model_catalog(app) -> None:
    if getattr(app, "_model_catalog_initialized", False):
        return
    app._model_catalog_initialized = True
    app._model_catalog_refreshing = False
    app._model_catalog_request_id = 0
    app._model_catalog_notice_text = ""
    state_dir = getattr(app, "_state_dir", None)
    app._model_catalog_state = (
        model_catalog.load_model_catalog_state(state_dir) if state_dir is not None else ModelCatalogState()
    )
    _install_runtime_validation_hook(app)
    render_model_catalog(app)


def start_model_catalog_refresh(app) -> None:
    if getattr(app, "_model_catalog_refreshing", False):
        return
    _flush_runtime_settings_if_available(app)
    _refresh_credentials_view_if_ready(app)
    app._model_catalog_request_id = getattr(app, "_model_catalog_request_id", 0) + 1
    app._model_catalog_refreshing = True
    render_model_catalog(app, notice="Refreshing models...")
    request_id = app._model_catalog_request_id
    threading.Thread(target=_refresh_worker, args=(app, request_id), daemon=True).start()


def finish_model_catalog_refresh(app, request_id: int, *, result=None, error: str = "") -> None:
    if request_id != getattr(app, "_model_catalog_request_id", 0):
        return
    app._model_catalog_refreshing = False
    if error:
        render_model_catalog(app, notice=f"Refresh Models failed: {error}")
        return
    app._model_catalog_state = result.state
    state_dir = getattr(app, "_state_dir", None)
    if state_dir is not None:
        model_catalog.save_model_catalog_state(state_dir, result.state)
    render_model_catalog(app, notice=_refresh_notice(result.group_results))


def render_model_catalog(app, *, notice: str | None = None) -> None:
    if notice is not None:
        app._model_catalog_notice_text = notice
    try:
        runtime_settings = repository.current_runtime_settings(app)
    except Exception:
        runtime_settings = getattr(app, "_runtime_settings", None)
    effective = model_catalog.effective_model_catalog_state(
        getattr(app, "_model_catalog_state", ModelCatalogState()),
        runtime_settings or repository.default_runtime_settings(),
    )
    app._model_catalog_effective_state = effective
    _render_group_labels(app, effective)
    _render_model_widgets(app, effective)
    _render_notice(app)
    if hasattr(app, "_update_button_state"):
        app._update_button_state()


def _refresh_worker(app, request_id: int) -> None:
    try:
        state_dir = getattr(app, "_state_dir", None)
        runtime_settings = repository.current_runtime_settings(app)
        result = model_catalog.refresh_model_catalogs(
            getattr(app, "_model_catalog_state", ModelCatalogState()),
            llm_shared_provider=runtime_settings.llm_shared_provider,
            optimizer_ocr_provider=runtime_settings.optimizer_ocr_provider,
            embeddings_provider=runtime_settings.embeddings_provider,
            shared_llm_api_key=_catalog_api_key(state_dir, "llm_shared", runtime_settings.llm_shared_provider),
            optimizer_ocr_api_key=_catalog_api_key(state_dir, "optimizer_ocr", runtime_settings.optimizer_ocr_provider),
            embeddings_api_key=_catalog_api_key(state_dir, "embeddings", runtime_settings.embeddings_provider),
        )
    except Exception as exc:  # pragma: no cover - UI thread handoff
        app.after(0, lambda: finish_model_catalog_refresh(app, request_id, error=str(exc)))
        return
    app.after(0, lambda: finish_model_catalog_refresh(app, request_id, result=result))


def _catalog_api_key(state_dir, target: str, provider_settings) -> str | None:
    if state_dir is None:
        return None
    return credentials.load_api_key(state_dir, target, provider_settings=provider_settings)


def _flush_runtime_settings_if_available(app) -> None:
    if hasattr(app, "_flush_pending_save"):
        app._flush_pending_save("runtime_settings")


def _refresh_credentials_view_if_ready(app) -> None:
    if not hasattr(app, "_refresh_credentials_view"):
        return
    if not hasattr(app, "_credential_widgets") or not hasattr(app, "_credentials_notice_label"):
        return
    app._refresh_credentials_view()


def _install_runtime_validation_hook(app) -> None:
    if getattr(app, "_model_catalog_hook_installed", False) or not hasattr(app, "_update_button_state"):
        return
    base_update = app._update_button_state

    def _wrapped_update() -> None:
        base_update()
        error = _runtime_settings_error(app)
        if error:
            app._start_btn.configure(state="disabled")

    app._update_button_state = _wrapped_update
    app._model_catalog_hook_installed = True


def _runtime_settings_error(app) -> str:
    try:
        repository.current_runtime_settings(app)
    except Exception as exc:
        return str(exc)
    return ""


def _render_group_labels(app, effective_state) -> None:
    for target, label in getattr(app, "_model_catalog_group_labels", {}).items():
        group = effective_state.group_for(target)
        provider_detail = _provider_detail(group)
        if group.refreshed_at:
            text = f"{_GROUP_LABELS[target]}: {len(group.models)} models | {group.refreshed_at} | {provider_detail}"
        elif group.models:
            text = f"{_GROUP_LABELS[target]}: seed from runtime_settings.json ({len(group.models)} models) | {provider_detail}"
        else:
            text = f"{_GROUP_LABELS[target]}: no model available yet"
        label.configure(text=text)


def _render_model_widgets(app, _effective_state) -> None:
    for section, widgets in getattr(app, "_runtime_settings_widgets", {}).items():
        selector = widgets["model"]
        selected = str(selector.get() or "").strip()
        options = list(repository.catalog_models_for_section(app, section))
        resolved_selected = repository.resolve_catalog_model_for_section(app, section, selected)
        invalid = bool(options) and selected and resolved_selected not in options
        if selected and resolved_selected in options:
            selected = resolved_selected
        if selected and selected not in options:
            options.insert(0, selected)
        selector.configure(values=options or [selected or "No models"])
        if selected:
            selector.set(selected)
        elif options:
            selector.set(options[0])
        widgets["model_status"].configure(
            text="No longer in the current provider catalog" if invalid else "Provider catalog valid",
            text_color=theme.COLOR_WARNING if invalid else theme.COLOR_MUTED,
        )


def _render_notice(app) -> None:
    label = getattr(app, "_model_catalog_notice_label", None)
    if label is None:
        return
    text = getattr(app, "_model_catalog_notice_text", "").strip()
    label.configure(text=text, text_color=theme.COLOR_WARNING if text else theme.COLOR_MUTED)
    button = getattr(app, "_model_catalog_refresh_button", None)
    if button is not None:
        button.configure(
            state="disabled" if getattr(app, "_model_catalog_refreshing", False) else "normal",
            text="Refreshing..." if getattr(app, "_model_catalog_refreshing", False) else "Refresh Models",
        )


def _refresh_notice(group_results: dict[str, object]) -> str:
    messages: list[str] = []
    seen: set[str] = set()
    for result in group_results.values():
        message = str(getattr(result, "message", "") or "").strip()
        if not message or message in seen:
            continue
        seen.add(message)
        messages.append(message)
    return " | ".join(messages)


def _provider_detail(group) -> str:
    provider_id = str(getattr(group, "provider_id", "") or "").strip() or "provider"
    base_url = str(getattr(group, "base_url", "") or "").strip()
    label = provider_definition(provider_id).display_name if provider_id != "provider" else provider_id
    return f"{label} @ {base_url}" if base_url else label
