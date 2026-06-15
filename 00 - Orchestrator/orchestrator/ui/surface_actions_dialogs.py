"""Dialog, launcher, and help action mixins for the desktop surface."""

from __future__ import annotations

from pathlib import Path

from . import dialogs, edit_suite_launcher, status_help


class OrchestratorAppDialogActions:
    def _browse_input_folder(self) -> None:
        self._set_entry_path(self._input_entry, dialogs.select_input_folder(self))

    def _browse_artifact_folder(self) -> None:
        self._set_entry_path(self._artifact_entry, dialogs.select_artifact_folder(self))

    def _browse_release_file(self) -> None:
        self._set_entry_path(self._release_entry, dialogs.select_release_file(self))

    def _browse_corpus_folder(self) -> None:
        previous_storage = self._corpus_entry.get().strip()
        previous_selected = self._selected_db_entry.get().strip() if hasattr(self, "_selected_db_entry") else ""
        selected = dialogs.select_corpus_folder(self)
        self._set_entry_path(self._corpus_entry, selected)
        if hasattr(self, "_selected_db_entry") and selected:
            if not previous_selected:
                self._set_entry_path(self._selected_db_entry, str(Path(selected) / "corpus.db"))
            else:
                try:
                    if previous_storage and Path(previous_selected).resolve().is_relative_to(Path(previous_storage).resolve()):
                        self._set_entry_path(self._selected_db_entry, str(Path(selected) / Path(previous_selected).name))
                except Exception:
                    pass
        self._refresh_database_status()

    def _browse_database_file(self) -> None:
        initial_dir = self._corpus_entry.get().strip() if hasattr(self, "_corpus_entry") else ""
        selected = dialogs.select_database_file(self, initial_dir=initial_dir or None)
        if selected and hasattr(self, "_corpus_entry"):
            self._set_entry_path(self._corpus_entry, str(Path(selected).parent))
        self._set_entry_path(self._selected_db_entry, selected)
        self._refresh_database_status()

    def _open_edit_suite(self) -> None:
        try:
            script_path = edit_suite_launcher.launch(self._project_root)
            self._append_log(f"[INFO] Edit Suite started via {script_path}")
        except Exception as exc:
            self._append_log(f"[ERROR] Edit Suite start failed: {exc}")
            dialogs.show_error(str(exc))

    def _show_status_help(self) -> None:
        dialogs.show_info_window(self, title=status_help.STATUS_TITLE, body=status_help.STATUS_BODY)
