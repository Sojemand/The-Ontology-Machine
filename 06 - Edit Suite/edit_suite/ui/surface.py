"""Thin surface class for the Edit Suite desktop UI."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from ..bootstrap import EDIT_SUITE_ROOT, ensure_startup_prerequisites
from ..policy import SECTION_ORDER
from ..repository import load_ui_state, save_ui_state
from ..surfaces import DraftState, validate_draft, write_draft
from . import draft_reading, layout, loading_workflow, operation_runner, responsive, surface_actions, surface_state, theme, view_model
from . import workflow as ui_workflow


class EditSuiteApp(ctk.CTk):
    """Desktop UI for registry, readiness and owner-provided edit surfaces."""

    def __init__(self, project_root: Path | None = None) -> None:
        theme.apply_theme()
        super().__init__()
        context = ensure_startup_prerequisites(project_root or EDIT_SUITE_ROOT)
        self._pipeline_root = context.pipeline_root
        self._state_root = context.state_root
        self._ui_state = load_ui_state(self._state_root)
        self._snapshot = loading_workflow.initial_snapshot(self._state_root)
        self._bundles: dict[str, object] = {}
        self._bundle_errors: dict[str, str] = {}
        self._bundle_loading: set[str] = set()
        self._bundle_live_slots: set[str] = set()
        self._bundle_failed_slots: set[str] = set()
        self._drafts: dict[str, dict[str, DraftState]] = {}
        self._action_widgets: dict[str, dict] = {}
        self._operation_results: dict[str, dict] = {}
        self._operation_action_loading: set[str] = set()
        self._request_tokens: dict[str, int] = {}
        self._surface_action_loading: set[str] = set()
        self._render_detail_only = False
        self.title("Edit Suite")
        self.geometry(responsive.restore_window_geometry(self, self._ui_state["window_geometry"]))
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self._shell = layout.build_shell(self, on_tab_change=lambda: ui_workflow.on_tab_selected(self))
        ui_workflow.configure(self)
        self._selected_module = self._restore_selection()
        self._render()
        self.after(0, lambda: loading_workflow.refresh_registry(self))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def refresh_registry(self) -> None:
        loading_workflow.refresh_registry(self)

    def select_module(self, slot_name: str) -> None:
        self._ui_state["selected_section"] = self._current_section()
        self._selected_module = slot_name
        self._ui_state["selected_module"] = slot_name
        self._operation_results.clear()
        self._render_detail_only = False
        self._render()

    def validate_surface(self, surface_id: str) -> None:
        self._apply_surface_action(surface_id, validate_draft)

    def save_surface(self, surface_id: str) -> None:
        self._apply_surface_action(surface_id, write_draft, refresh_bundle=True)

    def run_surface_action(self, surface_id: str, action_link: dict) -> None:
        operation_runner.run_surface_action(self, surface_id, action_link)

    def resolve_merge_interaction(self, surface_id: str, choice_id: str) -> None:
        operation_runner.resolve_merge_interaction(self, surface_id, choice_id)

    def operation_result_text(self, surface_id: str) -> str:
        return operation_runner.result_text(self, surface_id)

    def entry_is_loading(self) -> bool:
        return loading_workflow.entry_is_loading(self)

    def action_button_state(self, surface_id: str) -> str:
        return surface_actions.action_button_state(self, surface_id)

    def _restore_selection(self) -> str:
        return view_model.preferred_module_key(self._snapshot, self._ui_state["selected_module"])

    def _current_section(self) -> str:
        allowed = {name for name, _label in SECTION_ORDER}
        selected = self._ui_state["selected_section"]
        shell = self._state_dict().get("_shell")
        if isinstance(shell, dict):
            live_selected = str(shell["tabs"].get() or "")
            if live_selected in allowed:
                selected = live_selected
        return selected if selected in allowed else "Summary"

    def _selected_entry(self):
        for entry in self._snapshot.entries:
            if entry.slot_name == self._selected_module:
                return entry
        return None

    def _render(self) -> None:
        detail_only = self._render_detail_only
        self._render_detail_only = False
        ui_workflow.render(self, detail_only=detail_only)

    def _apply_surface_action(self, surface_id: str, action, *, refresh_bundle: bool = False) -> None:
        surface_actions.apply_surface_action(self, surface_id, action, refresh_bundle=refresh_bundle)

    def _finish_surface_action(
        self,
        token_name: str,
        token: int,
        entry,
        surface_id: str,
        result,
        error: Exception | None,
        refresh_bundle: bool,
        value: dict,
    ) -> None:
        surface_actions.finish_surface_action(self, token_name, token, entry, surface_id, result, error, refresh_bundle, value)

    def _read_widget_value(self, surface_id: str) -> dict:
        return draft_reading.read_widget_value(self._action_widgets_state(), surface_id)

    def _fallback_draft_value(self, surface_id: str) -> dict:
        return draft_reading.fallback_draft_value(self._action_widgets_state(), surface_id)

    def _remember_saved_draft(self, entry, draft: DraftState) -> None:
        loading_workflow.remember_saved_draft(self, entry, draft)

    def _ensure_bundle(self, entry) -> None:
        loading_workflow.ensure_bundle(self, entry)

    def _reload_bundle(self, entry) -> None:
        loading_workflow.ensure_bundle(self, entry, force=True, rerender=True)

    def _persist_ui_state(self) -> None:
        self._ui_state["window_geometry"] = self.geometry()
        self._ui_state["selected_module"] = self._selected_module
        self._ui_state["selected_section"] = self._shell["tabs"].get()
        save_ui_state(self._state_root, self._ui_state)

    def _on_close(self) -> None:
        self._persist_ui_state()
        self.destroy()

    def _state_dict(self) -> dict:
        return surface_state.state_dict(self)

    def _has_async_ui(self) -> bool:
        return surface_state.has_async_ui(self)

    def _action_widgets_state(self) -> dict[str, dict]:
        return surface_state.action_widgets_state(self)

    def _surface_action_loading_state(self) -> set[str]:
        return self._private_set("_surface_action_loading")

    def _operation_action_loading_state(self) -> set[str]:
        return self._private_set("_operation_action_loading")

    def _private_set(self, name: str) -> set[str]:
        return surface_state.private_set(self, name)

    def _private_mapping(self, name: str) -> dict:
        return surface_state.private_mapping(self, name)

    def _evict_bundle(self, entry) -> None:
        surface_state.evict_bundle(self, entry)
