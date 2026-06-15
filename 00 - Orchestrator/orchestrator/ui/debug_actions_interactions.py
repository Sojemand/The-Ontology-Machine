"""Interaction helpers for the orchestrator debug-host tab."""

from __future__ import annotations

import os
from pathlib import Path

from .. import debug_host
from . import debug_artifact_list, debug_help, debug_repository, dialogs
from .debug_actions_session import apply_debug_view, debug_session_running


def reset_debug_output(self) -> None:
    if debug_session_running(getattr(self, "_debug_session", None)):
        dialogs.show_error("Reset Debug Output is locked while a debug session is running.")
        return
    if not dialogs.confirm_reset_debug_output(self):
        return
    try:
        self._stop_debug_session_poll()
        debug_host.clear_sessions(state_root=self._state_dir)
        debug_artifact_list.reset_hidden_paths(self)
        self._debug_session = None
        self._selected_debug_artifact_index = 0
        debug_repository.clear_persisted_hidden_paths(self)
        apply_debug_view(self, scope="full")
    except Exception as exc:
        dialogs.show_error(str(exc))


def dismiss_debug_artifact(self, path) -> None:
    entries = list(getattr(self, "_debug_artifact_entries", ()))
    target_path = Path(path)
    target_index = next((index for index, entry in enumerate(entries) if getattr(entry, "path", None) == target_path), None)
    if target_index is None:
        return
    if _clear_single_file_import(self, entries[target_index], target_path):
        self._selected_debug_artifact_index = 0
        self._save_debug_state()
        apply_debug_view(self, scope="full")
        return
    current_index = int(getattr(self, "_selected_debug_artifact_index", 0) or 0)
    debug_artifact_list.dismiss_path(self, target_path)
    if current_index > target_index:
        current_index -= 1
    elif current_index == target_index and current_index >= len(entries) - 1:
        current_index = max(0, current_index - 1)
    self._selected_debug_artifact_index = current_index if len(entries) > 1 else 0
    self._save_debug_state()
    apply_debug_view(self, scope="full")


def open_debug_artifacts(self) -> None:
    if self._debug_session is None:
        return
    target = self._debug_session.session_root if self._debug_session.session_root.exists() else self._debug_session.output_root
    try:
        os.startfile(target)  # type: ignore[attr-defined]
    except Exception as exc:
        dialogs.show_error(str(exc))


def show_debug_help(self) -> None:
    help_entry = debug_help.get_help(str(self._current_debug_state().get("module_key", "")))
    if help_entry is None:
        dialogs.show_error("No module-specific debug help is available for the selected target.")
        return
    title, body = help_entry
    dialogs.show_info_window(self, title=title, body=body)


def load_debug_artifact_file(self) -> None:
    path = dialogs.select_debug_artifact_file(self)
    if not path:
        return
    debug_artifact_list.reset_hidden_paths(self)
    self._debug_artifact_import_entry.delete(0, "end")
    self._debug_artifact_import_entry.insert(0, path)
    self._selected_debug_artifact_index = 0
    self._save_debug_state()
    apply_debug_view(self, scope="full")


def load_debug_artifact_dir(self) -> None:
    path = dialogs.select_debug_artifact_dir(self)
    if not path:
        return
    debug_artifact_list.reset_hidden_paths(self)
    self._debug_artifact_import_entry.delete(0, "end")
    self._debug_artifact_import_entry.insert(0, path)
    self._selected_debug_artifact_index = 0
    self._save_debug_state()
    apply_debug_view(self, scope="full")


def clear_debug_artifact_import(self) -> None:
    debug_artifact_list.reset_hidden_paths(self)
    self._debug_artifact_import_entry.delete(0, "end")
    self._selected_debug_artifact_index = 0
    self._save_debug_state()
    apply_debug_view(self, scope="full")


def select_debug_artifact(self, index: int) -> None:
    self._selected_debug_artifact_index = index
    apply_debug_view(self, scope="full")


def browse_debug_input(self) -> None:
    state = self._current_debug_state()
    descriptor = debug_repository.descriptor_for_state(self, state)
    picker = debug_repository.input_picker_options(state, descriptor=descriptor)
    path = dialogs.select_debug_input_path(self, **picker)
    if not path:
        return
    self._debug_input_entry.delete(0, "end")
    self._debug_input_entry.insert(0, path)
    self._on_debug_change()
    self._flush_pending_save("debug_state")


def browse_debug_source(self) -> None:
    path = dialogs.select_debug_source_path(self)
    if not path:
        return
    self._debug_source_entry.delete(0, "end")
    self._debug_source_entry.insert(0, path)
    self._on_debug_change()
    self._flush_pending_save("debug_state")


def debug_launch_paths(self, state, descriptor) -> tuple[Path | str, str]:
    mode = str(state.get("mode", "")).strip().lower()
    if debug_repository.uses_module_selected_input(descriptor):
        input_path = Path(str(state.get("input_path", "")).strip())
        if mode == "single":
            return input_path.parent, str(input_path)
        return input_path, ""
    if mode == "single":
        source_path = str(state.get("source_path", "")).strip()
        return _input_root_for_single_source(source_path, state), source_path
    return str(state.get("input_path", "")).strip(), ""


def _input_root_for_single_source(source_path: str, state: dict[str, object] | None = None) -> Path | str:
    if not source_path:
        return ""
    candidate = Path(source_path)
    if candidate.is_absolute():
        return candidate.parent
    return str((state or {}).get("input_path", "")).strip()


def _clear_single_file_import(app, entry, target_path: Path) -> bool:
    if str(getattr(entry, "source", "")).strip().lower() != "import":
        return False
    import_entry = getattr(app, "_debug_artifact_import_entry", None)
    import_text = str(import_entry.get() if import_entry is not None and hasattr(import_entry, "get") else "").strip()
    if not import_text:
        return False
    import_path = Path(import_text)
    if import_path != target_path or not import_path.suffix:
        return False
    import_entry.delete(0, "end")
    hidden = getattr(app, "_hidden_debug_artifact_paths", None)
    if isinstance(hidden, set):
        hidden.discard(str(target_path))
    return True
