"""Rendering helpers for the orchestrator debug-host tab."""

from __future__ import annotations

from pathlib import Path

from ..debug_host import has_sessions, plan_for
from ..debug_host.polling import load_log
from . import debug_artifact_list, debug_artifacts, debug_help, debug_repository, debug_view_support
from .debug_controls_layout import apply_console_state


def apply_view(app, *, scope: str = "full") -> None:
    state = app._current_debug_state()
    descriptor = debug_repository.descriptor_for_state(app, state)
    modes = list(debug_repository.supported_modes_for_module(app, str(state.get("module_key", ""))))
    _configure_target_selectors(app, state, modes)
    apply_console_state(app, descriptor, state)
    if descriptor is None:
        _apply_placeholder_console(app)
        _apply_placeholder_monitor(app, state)
    else:
        _apply_monitor(app, descriptor, state)
    if scope == "full":
        _apply_artifact_view(app, getattr(app, "_debug_session", None), str(state.get("artifact_import_path", "")))
        session = getattr(app, "_debug_session", None)
        debug_view_support.set_box(app._debug_log_box, load_log(session.run_log_path) if session is not None else "")
    update_buttons(app)


def update_buttons(app) -> None:
    state = app._current_debug_state()
    descriptor = debug_repository.descriptor_for_state(app, state)
    session = getattr(app, "_debug_session", None)
    running = _session_running(session)
    app._debug_start_btn.configure(state="normal" if _has_required_input(app, state, descriptor) and _has_required_source(state, descriptor) and not running else "disabled")
    app._debug_refresh_btn.configure(state="normal" if session is not None else "disabled")
    app._debug_cancel_btn.configure(state="normal" if running else "disabled")
    app._debug_open_btn.configure(state="normal" if session is not None else "disabled")
    reset_button = getattr(app, "_debug_reset_output_btn", None)
    if reset_button is not None:
        reset_button.configure(
            state="normal" if not running and has_sessions(state_root=getattr(app, "_state_dir", None)) else "disabled"
        )
    help_button = getattr(app, "_debug_help_btn", None)
    if help_button is not None:
        help_button.configure(state="normal" if debug_help.has_help(str(state.get("module_key", ""))) else "disabled")
    if hasattr(app, "_debug_artifact_import_entry"):
        state_name = "disabled" if running else "normal"
        app._debug_artifact_import_entry.configure(state=state_name)
        for attr_name in ("_debug_replay_load_file_btn", "_debug_replay_load_dir_btn", "_debug_replay_clear_btn"):
            widget = getattr(app, attr_name, None)
            if widget is not None:
                widget.configure(state=state_name)


def _configure_target_selectors(app, state: dict[str, object], modes: list[str]) -> None:
    app._debug_module_menu.configure(values=debug_repository.module_menu_values(app))
    app._debug_module_menu.set(debug_repository.module_label(app, state.get("module_key", "")))
    app._debug_mode_menu.configure(values=modes)
    app._debug_mode_menu.configure(state="disabled" if len(modes) == 1 else "normal")
    if state["mode"] not in modes:
        app._debug_mode_menu.set(modes[0])


def _apply_placeholder_console(app) -> None:
    for key in ("input_path", "source_path"):
        debug_view_support.set_row_visible(app._debug_control_rows.get(key), False)
    for attr_name in ("_debug_input_entry", "_debug_source_entry"):
        widget = getattr(app, attr_name, None)
        if widget is not None:
            widget.configure(state="disabled")
    app._debug_target_hint_label.configure(text="This menu entry is reserved as a placeholder. Debug-host execution is not wired for it yet.")


def _apply_placeholder_monitor(app, state: dict[str, object]) -> None:
    label = debug_repository.module_label(app, state.get("module_key", ""))
    app._debug_plan_label.configure(text="Plan: placeholder module. No debug contract is available yet.")
    app._debug_status_label.configure(text=f"{label} | PLACEHOLDER")
    app._debug_detail_label.configure(text="Select a wired module to start a debug session.")
    debug_view_support.set_label(app._debug_metrics_label, "")


def _apply_monitor(app, descriptor, state: dict[str, object]) -> None:
    plan = plan_for(
        descriptor.module_key,
        str(state.get("mode", "")),
        registry_path=app._project_root / "module-registry.json",
    )
    labels = [
        "Request Enrichment" if step.kind == "host_step" else f"{step.module_key}:{step.action}"
        for step in getattr(plan, "steps", ())
    ]
    app._debug_plan_label.configure(text=f"Plan: {' -> '.join(labels)}")
    session = getattr(app, "_debug_session", None)
    if session is None:
        app._debug_status_label.configure(text=f"{descriptor.display_name} | READY")
        app._debug_detail_label.configure(text="No session started yet.")
        debug_view_support.set_label(app._debug_metrics_label, "")
        return
    app._debug_status_label.configure(text=f"{descriptor.display_name} | {debug_view_support.session_status(session)}")
    app._debug_detail_label.configure(text=debug_view_support.session_detail(session) or "Session ohne Detailtext.")
    debug_view_support.set_label(app._debug_metrics_label, debug_view_support.metrics_text(session))


def _apply_artifact_view(app, session, import_path: str) -> None:
    all_imported_entries = debug_artifacts.import_entries(import_path)
    imported_entries = debug_artifact_list.visible_entries(app, all_imported_entries)
    entries = debug_artifact_list.visible_entries(app, debug_artifacts.collect_entries(session, import_path))
    setattr(app, "_debug_artifact_entries", entries)
    debug_view_support.set_label(app._debug_artifact_summary_label, debug_artifacts.summary_text(entries) or "No artifacts loaded.")
    index = min(int(getattr(app, "_selected_debug_artifact_index", 0) or 0), max(len(entries) - 1, 0))
    debug_artifact_list.render_entries(app, entries, selected_index=index)
    setattr(app, "_selected_debug_artifact_index", index)
    selected = entries[index] if entries else None
    debug_view_support.set_box(app._debug_preview_box, debug_artifacts.preview_text(selected))
    _apply_replay_view(app, import_path, imported_entries, all_imported_entries=all_imported_entries)


def _apply_replay_view(
    app,
    import_path: str,
    imported_entries: list[debug_artifacts.ArtifactEntry],
    *,
    all_imported_entries: list[debug_artifacts.ArtifactEntry],
) -> None:
    path_text = str(import_path or "").strip()
    if not path_text:
        debug_view_support.set_label(app._debug_replay_status_label, "No replay loaded.")
        debug_view_support.set_box(app._debug_replay_box, "Load file/Load dir attaches versioned or local artifacts for offline inspection.")
        return
    if all_imported_entries and not imported_entries:
        debug_view_support.set_label(app._debug_replay_status_label, f"Replay loaded: {Path(path_text).name} | all artifacts removed")
        debug_view_support.set_box(app._debug_replay_box, "All loaded replay artifacts were removed from the view.")
        return
    if not imported_entries:
        debug_view_support.set_label(app._debug_replay_status_label, f"Replay path without readable artifacts: {path_text}")
        debug_view_support.set_box(app._debug_replay_box, path_text)
        return
    debug_view_support.set_label(app._debug_replay_status_label, f"Replay loaded: {Path(path_text).name}")
    debug_view_support.set_box(app._debug_replay_box, "\n".join(entry.summary for entry in imported_entries))


def _has_required_input(app, state: dict[str, object], descriptor) -> bool:
    if descriptor is None:
        return False
    mode = str(state.get("mode", "")).strip().lower()
    if not debug_repository.uses_module_selected_input(descriptor) and mode == "single":
        return True
    return bool(str(state.get("input_path", "")).strip())


def _has_required_source(state: dict[str, object], descriptor) -> bool:
    if descriptor is None or debug_repository.uses_module_selected_input(descriptor):
        return descriptor is not None
    return state["mode"] != "single" or bool(str(state["source_path"]).strip())


def _session_running(session) -> bool:
    return bool(
        session is not None
        and session.active_step is not None
        and (session.result is None or session.result.status not in {"ok", "error", "cancelled"})
    )
