"""Thin surface class for the Orchestrator desktop UI."""
from __future__ import annotations

import logging
import multiprocessing as mp
from pathlib import Path

import customtkinter as ctk

from ..bootstrap import ORCHESTRATOR_ROOT
from ..models import PipelineSnapshot
from ..state import load_runtime_settings, load_ui_state
from . import dialogs, responsive, save_scheduler, theme
from .debug_actions import DebugHostAppActions
from .pipeline_log_reset_actions import PipelineLogResetAppActions
from .surface_actions import OrchestratorAppActions


class OrchestratorApp(DebugHostAppActions, PipelineLogResetAppActions, OrchestratorAppActions, ctk.CTk):
    """Desktop UI for end-to-end pipeline orchestration."""

    def __init__(self, project_root: Path | None = None) -> None:
        theme.apply_theme()
        super().__init__()
        self._project_root = Path(project_root or ORCHESTRATOR_ROOT)
        self._state_dir = self._project_root / "state"
        self._ui_state_path = self._state_dir / "ui_state.json"
        self._debug_state_path = self._state_dir / "debug_host_state.json"
        self._ui_state = load_ui_state(self._ui_state_path)
        self._runtime_settings = load_runtime_settings(self._state_dir)
        self._credentials_state = None
        self._credentials_profile = None
        self._debug_descriptors = {}
        self._debug_session = None
        self._debug_session_poll_handle = None
        self._debug_artifact_entries = []
        self._hidden_debug_artifact_paths = set()
        self._selected_debug_artifact_index = 0
        self._log_lines: list[str] = []
        self._processing = False
        self._stop_requested = False
        self._active_action = ""
        self._snapshot = PipelineSnapshot()
        self._mp_context = mp.get_context("spawn")
        self._worker_process = None
        self._worker_queue = None
        self._worker_cancel_event = None
        self._queue_poll_handle = None
        save_scheduler.configure(self)
        self.title("Orchestrator")
        self.geometry(responsive.fit_window_geometry(self))
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self._build_ui()
        self._restore_ui_state()
        self._restore_runtime_settings()
        self._apply_snapshot(self._snapshot)
        self._update_button_state()
        self._refresh_database_status()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def report_callback_exception(self, exc, val, tb) -> None:  # pragma: no cover - exercised by live Tk callbacks
        logging.getLogger(__name__).error("Tkinter callback failed", exc_info=(exc, val, tb))
        message = str(val or "").strip() or getattr(exc, "__name__", "Unknown Tkinter error")
        append_log = getattr(self, "_append_log", None)
        if callable(append_log):
            try:
                append_log(f"[ERROR] UI callback failed: {message}")
            except Exception:
                pass
        try:
            dialogs.show_error(f"{message}\n\nDetails are available in state/orchestrator.log.")
        except Exception:
            pass
