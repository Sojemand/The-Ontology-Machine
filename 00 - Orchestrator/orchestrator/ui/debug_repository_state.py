"""State persistence helpers for the orchestrator debug-host tab."""

from __future__ import annotations

from ..state.adapter import atomic_json_write, load_json_object
from . import debug_artifact_list, debug_state_support
from . import debug_repository_catalog as catalog


def read_state(app) -> dict[str, object]:
    module_key = _normalize_module_key(app, app._debug_module_var.get())
    mode = _normalize_mode(app, module_key, app._debug_mode_var.get())
    return {
        "module_key": module_key,
        "mode": mode,
        "input_path": debug_state_support.widget_text(getattr(app, "_debug_input_entry", None)),
        "source_path": debug_state_support.widget_text(getattr(app, "_debug_source_entry", None)),
        "format": debug_state_support.widget_text(getattr(app, "_debug_format_entry", None)),
        "doc_type": debug_state_support.widget_text(getattr(app, "_debug_doc_type_entry", None)),
        "max_size_mb": debug_state_support.widget_text(getattr(app, "_debug_size_entry", None)),
        "batch_size": debug_state_support.widget_text(getattr(app, "_debug_batch_entry", None)),
        "worker_count": debug_state_support.widget_text(getattr(app, "_debug_worker_entry", None)),
        "use_processed_hashes": bool(debug_state_support.bool_value(getattr(app, "_debug_hash_var", None), default=True)),
        "raw_path": debug_state_support.widget_text(getattr(app, "_debug_raw_entry", None)),
        "raw_root": debug_state_support.widget_text(getattr(app, "_debug_raw_root_entry", None)),
        "artifact_import_path": debug_state_support.widget_text(getattr(app, "_debug_artifact_import_entry", None)),
        "dismissed_artifact_paths": debug_artifact_list.persisted_hidden_paths(app),
        "persist_page_images_in_db": bool(debug_state_support.bool_value(getattr(app, "_debug_persist_page_images_var", None), default=False)),
        "check_free_text": bool(debug_state_support.bool_value(getattr(app, "_debug_check_free_text_var", None), default=True)),
        "check_context_scalars": bool(debug_state_support.bool_value(getattr(app, "_debug_check_context_scalars_var", None), default=True)),
        "check_content_fields": bool(debug_state_support.bool_value(getattr(app, "_debug_check_content_fields_var", None), default=True)),
        "check_rows": bool(debug_state_support.bool_value(getattr(app, "_debug_check_rows_var", None), default=True)),
    }


def restore_state(app) -> dict[str, object]:
    defaults = _default_state(app)
    raw_data = load_json_object(
        app._debug_state_path,
        read_error="Could not load debug host state: %s",
        invalid_format="Debug-Host-State hat ungueltiges Format: %s",
    ) or {}
    data = _sanitize_persisted_state(raw_data, defaults=defaults)
    if data != raw_data:
        atomic_json_write(app._debug_state_path, data)
    module_key = _normalize_module_key(app, data.get("module_key", defaults["module_key"]))
    mode = _normalize_mode(app, module_key, data.get("mode", defaults["mode"]))
    app._suspend_surface_events = True
    try:
        debug_state_support.set_text(app._debug_module_menu, catalog.module_label(app, module_key))
        debug_state_support.set_text(app._debug_mode_menu, mode)
        _restore_fields(app, data, defaults)
        debug_artifact_list.restore_hidden_paths(app, data.get("dismissed_artifact_paths", defaults["dismissed_artifact_paths"]))
    finally:
        app._suspend_surface_events = False
    return read_state(app)


def save_state(app) -> dict[str, object]:
    state = read_state(app)
    atomic_json_write(app._debug_state_path, _sanitize_persisted_state(state, defaults=_default_state(app)))
    return state


def clear_persisted_hidden_paths(app) -> None:
    data = load_json_object(
        app._debug_state_path,
        read_error="Could not load debug host state: %s",
        invalid_format="Debug-Host-State hat ungueltiges Format: %s",
    )
    if not data or not data.get("dismissed_artifact_paths"):
        return
    data["dismissed_artifact_paths"] = []
    atomic_json_write(app._debug_state_path, data)


def runtime_options(state: dict[str, object], *, descriptor=None) -> dict[str, object]:
    options: dict[str, object] = {}
    controls = set(getattr(descriptor, "controls", ())) if descriptor is not None else None
    if controls is None or "filters" in controls:
        options["filters"] = {
            "format": debug_state_support.text_value(state.get("format")) or None,
            "doc_type": debug_state_support.text_value(state.get("doc_type")) or None,
            "max_size_mb": debug_state_support.int_value(state.get("max_size_mb")) or None,
            "batch_size": debug_state_support.int_value(state.get("batch_size")),
        }
    if controls is None or "worker_count" in controls:
        options["worker_count"] = max(1, debug_state_support.int_value(state.get("worker_count"), default=1))
    if controls is None or "hash_tools" in controls:
        options["hash_tools"] = {"use_processed_hashes": bool(state.get("use_processed_hashes"))}
    if controls is None or "raw_evidence" in controls:
        options["raw_evidence"] = {
            "raw_path": debug_state_support.text_value(state.get("raw_path")) or None,
            "raw_root": debug_state_support.text_value(state.get("raw_root")) or None,
        }
    if controls is None or "persist_page_images" in controls:
        options["persist_page_images_in_db"] = bool(state.get("persist_page_images_in_db"))
    if controls is None or "check_toggles" in controls:
        options["check_toggles"] = {
            "free_text": bool(state.get("check_free_text")),
            "context_scalars": bool(state.get("check_context_scalars")),
            "content_fields": bool(state.get("check_content_fields")),
            "rows": bool(state.get("check_rows")),
        }
    return options


def _restore_fields(app, data: dict[str, object], defaults: dict[str, object]) -> None:
    fields = (
        ("_debug_input_entry", "input_path"),
        ("_debug_source_entry", "source_path"),
        ("_debug_format_entry", "format"),
        ("_debug_doc_type_entry", "doc_type"),
        ("_debug_size_entry", "max_size_mb"),
        ("_debug_batch_entry", "batch_size"),
        ("_debug_worker_entry", "worker_count"),
        ("_debug_raw_entry", "raw_path"),
        ("_debug_raw_root_entry", "raw_root"),
        ("_debug_artifact_import_entry", "artifact_import_path"),
    )
    for attr_name, key in fields:
        debug_state_support.set_text(getattr(app, attr_name, None), str(data.get(key, defaults[key])))
    app._debug_hash_var.set(bool(data.get("use_processed_hashes", defaults["use_processed_hashes"])))
    debug_state_support.set_bool(getattr(app, "_debug_persist_page_images_var", None), bool(data.get("persist_page_images_in_db", defaults["persist_page_images_in_db"])))
    debug_state_support.set_bool(getattr(app, "_debug_check_free_text_var", None), bool(data.get("check_free_text", defaults["check_free_text"])))
    debug_state_support.set_bool(getattr(app, "_debug_check_context_scalars_var", None), bool(data.get("check_context_scalars", defaults["check_context_scalars"])))
    debug_state_support.set_bool(getattr(app, "_debug_check_content_fields_var", None), bool(data.get("check_content_fields", defaults["check_content_fields"])))
    debug_state_support.set_bool(getattr(app, "_debug_check_rows_var", None), bool(data.get("check_rows", defaults["check_rows"])))


def _default_state(app) -> dict[str, object]:
    module_key = catalog.default_module_key(app)
    return {
        "module_key": module_key,
        "mode": catalog.default_mode_for_module(app, module_key),
        **debug_state_support.DEFAULT_STATE,
    }


def _sanitize_persisted_state(data: object, *, defaults: dict[str, object]) -> dict[str, object]:
    payload = dict(data) if isinstance(data, dict) else {}
    payload["artifact_import_path"] = str(defaults.get("artifact_import_path", ""))
    return payload


def _normalize_module_key(app, value: object) -> str:
    descriptors = getattr(app, "_debug_descriptors", {})
    module_key = catalog.debug_module_catalog.key_for_value(value, descriptors)
    return module_key or catalog.default_module_key(app)


def _normalize_mode(app, module_key: str, value: object) -> str:
    mode = debug_state_support.text_value(value)
    modes = catalog.supported_modes_for_module(app, module_key)
    if mode in modes:
        return mode
    return modes[0]
