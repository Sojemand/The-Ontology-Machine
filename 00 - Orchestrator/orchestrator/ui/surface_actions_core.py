"""Core UI and worker action mixins for the desktop surface."""

from __future__ import annotations

from . import layout, rendering, repository, save_scheduler, theme, validation, worker_runtime, workflow


class OrchestratorAppCoreActions:
    def _build_ui(self) -> None:
        layout.build_ui(self)

    def _restore_ui_state(self) -> None:
        repository.restore_ui_state(self)

    def _current_ui_state(self):
        return repository.current_ui_state(self)

    def _save_ui_state(self) -> None:
        repository.save_ui_state(self)

    def _schedule_ui_state_save(self) -> None:
        save_scheduler.schedule(self, "ui_state", self._save_ui_state)

    def _restore_runtime_settings(self) -> None:
        repository.restore_runtime_settings(self)

    def _current_runtime_settings(self):
        return repository.current_runtime_settings(self)

    def _save_runtime_settings(self) -> None:
        repository.save_runtime_settings(self)

    def _persist_runtime_settings(self) -> None:
        self._save_runtime_settings()
        self._runtime_settings_notice_label.configure(
            text="Changes are saved directly under state/runtime_settings.json.",
            text_color=theme.COLOR_MUTED,
        )
        if hasattr(self, "_refresh_credentials_view") and hasattr(self, "_credential_widgets"):
            self._refresh_credentials_view()

    def _schedule_runtime_settings_save(self) -> None:
        save_scheduler.schedule(self, "runtime_settings", self._persist_runtime_settings)

    def _flush_pending_save(self, key: str) -> None:
        save_scheduler.flush(self, key)

    def _flush_pending_saves(self) -> None:
        save_scheduler.flush_all(self)

    def _on_ui_change(self) -> None:
        if getattr(self, "_suspend_surface_events", False):
            return
        self._schedule_ui_state_save()
        self._apply_snapshot(self._snapshot)
        self._update_button_state()

    def _on_mode_change(self) -> None:
        self._on_ui_change()
        self._flush_pending_save("ui_state")

    def _on_semantic_release_mode_change(self) -> None:
        self._on_ui_change()
        self._flush_pending_save("ui_state")

    def _on_runtime_settings_change(self) -> None:
        if getattr(self, "_suspend_surface_events", False):
            return
        try:
            repository.current_runtime_settings(self)
            self._runtime_settings_notice_label.configure(
                text="Changes are saved directly under state/runtime_settings.json.",
                text_color=theme.COLOR_MUTED,
            )
            self._schedule_runtime_settings_save()
        except Exception as exc:
            save_scheduler.cancel(self, "runtime_settings")
            self._runtime_settings_notice_label.configure(
                text=str(exc),
                text_color=theme.COLOR_WARNING,
            )
        self._update_button_state()

    def _update_button_state(self) -> None:
        fields = repository.read_fields(self)
        start_enabled = validation.can_start(fields, self._processing)
        activate_enabled = validation.can_activate_release(fields, self._processing)
        create_database_enabled = validation.can_create_database(fields, self._processing)
        abort_enabled = self._processing and not self._stop_requested
        self._start_btn.configure(state="normal" if start_enabled else "disabled")
        if hasattr(self, "_release_entry") and hasattr(self._release_entry, "configure"):
            release_widgets_state = "normal" if fields.semantic_release_mode == "override_selected" and not self._processing else "disabled"
            self._release_entry.configure(state=release_widgets_state)
        if hasattr(self, "_release_browse_btn"):
            self._release_browse_btn.configure(state="normal" if fields.semantic_release_mode == "override_selected" and not self._processing else "disabled")
        if hasattr(self, "_activate_release_btn"):
            self._activate_release_btn.configure(state="normal" if activate_enabled else "disabled")
        if hasattr(self, "_create_database_btn"):
            self._create_database_btn.configure(state="normal" if create_database_enabled else "disabled")
        if hasattr(self, "_create_artifact_tree_btn"):
            self._create_artifact_tree_btn.configure(state="disabled" if self._processing else "normal")
        self._abort_btn.configure(state="normal" if abort_enabled else "disabled")
        self._reset_btn.configure(state="disabled" if self._processing else "normal")
        if hasattr(self, "_debug_start_btn") and hasattr(self, "_update_debug_button_state"):
            self._update_debug_button_state()

    def _start_processing(self) -> None:
        workflow.start_processing(self)

    def _activate_selected_release(self) -> None:
        workflow.activate_selected_release(self)

    def _create_database(self) -> None:
        workflow.create_database(self)

    def _create_artifact_tree(self) -> None:
        workflow.create_artifact_tree(self)

    def _reset_run_history(self) -> None:
        workflow.reset_run_history(self)

    def _start_worker(self, *, action, ui_state, worker_payload=None) -> None:
        workflow.start_worker(self, action=action, ui_state=ui_state, worker_payload=worker_payload)

    def _abort_processing(self) -> None:
        workflow.abort_processing(self)

    def _force_stop_worker(self) -> None:
        workflow.force_stop_worker(self)

    def _drain_queue(self) -> None:
        workflow.drain_queue(self)

    def _finish_worker(self, *, cancelled: bool = False, error: str | None = None) -> None:
        workflow.finish_worker(self, cancelled=cancelled, error=error)

    def _mark_snapshot_aborted(self) -> None:
        workflow.mark_snapshot_aborted(self)

    def _active_stage_name(self) -> str | None:
        return workflow.active_stage_name(self)

    def _cleanup_worker_resources(self) -> None:
        worker_runtime.cleanup_worker_resources(self)

    def _wait_for_worker_exit(self, timeout: float = 0.5) -> None:
        worker_runtime.wait_for_worker_exit(self, timeout=timeout)

    def _apply_snapshot(self, snapshot) -> None:
        rendering.apply_snapshot(self, snapshot)

    def _refresh_database_status(self) -> None:
        workflow.refresh_database_status(self)

    def _append_log(self, line: str) -> None:
        rendering.append_log(self, line)

    def _clear_log(self) -> None:
        rendering.clear_log(self)

    def _set_entry_path(self, entry, path: str) -> None:
        repository.set_entry_path(self, entry, path)
        self._flush_pending_save("ui_state")

    def _on_close(self) -> None:
        self._flush_pending_saves()
        if hasattr(self, "_stop_debug_session_poll"):
            self._stop_debug_session_poll()
        worker_runtime.close_app(self)
