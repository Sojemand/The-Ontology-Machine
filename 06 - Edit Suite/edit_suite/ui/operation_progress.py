"""Small progress windows for long-running owner operations."""
from __future__ import annotations

from datetime import datetime
from time import monotonic
from typing import Any

import customtkinter as ctk

from . import theme
from .operation_progress_details import WARNING_COLOR, completion_detail, format_duration, should_show, status_color


class OperationProgressWindow:
    def __init__(self, app, *, surface_id: str, title: str, status: str, warning: str = "") -> None:
        self._app = app
        self._surface_id = surface_id
        self._started_at = datetime.now()
        self._started_monotonic = monotonic()
        self._finished = False
        self._after_id = None
        self.window = ctk.CTkToplevel(app)
        self.window.title(title)
        self.window.geometry("460x245")
        self.window.resizable(False, False)
        self.window.grid_columnconfigure(0, weight=1)
        self.window.protocol("WM_DELETE_WINDOW", self._close_if_finished)
        try:
            self.window.transient(app)
        except Exception:
            pass

        ctk.CTkLabel(self.window, text=title, font=theme.font_header(), anchor="w").grid(
            row=0,
            column=0,
            padx=theme.PADDING,
            pady=(theme.PADDING, theme.PADDING_SMALL),
            sticky="we",
        )
        self.status_label = ctk.CTkLabel(
            self.window,
            text=status,
            font=theme.font_normal(),
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.status_label.grid(row=1, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we")
        self.progress = ctk.CTkProgressBar(self.window, mode="indeterminate")
        self.progress.grid(row=2, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we")
        self.progress.start()
        self.detail_label = ctk.CTkLabel(
            self.window,
            text=self._running_detail(),
            font=theme.font_small(),
            text_color=theme.COLOR_MUTED,
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.detail_label.grid(row=3, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we")
        self.warning_label = ctk.CTkLabel(
            self.window,
            text=warning,
            font=theme.font_small(),
            text_color=WARNING_COLOR,
            anchor="w",
            justify="left",
            wraplength=420,
        )
        if warning:
            self.warning_label.grid(row=4, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we")
        self.close_button = ctk.CTkButton(self.window, text="Close", width=116, state="disabled", command=self.close)
        self.close_button.grid(row=5, column=0, padx=theme.PADDING, pady=(theme.PADDING_SMALL, theme.PADDING), sticky="e")
        self._tick()

    def complete(self, response: dict[str, Any]) -> None:
        if self._finished:
            return
        self._finished = True
        self._cancel_tick()
        self._stop_progress()
        status = str(response.get("status") or "completed").strip() or "completed"
        finished_at = datetime.now().strftime("%H:%M:%S")
        self.status_label.configure(text=f"Completed at {finished_at}", text_color=status_color(status))
        self.detail_label.configure(text=completion_detail(response, status=status))
        self.close_button.configure(state="normal")

    def fail(self, message: str) -> None:
        self.complete({"status": "error", "reason": message})

    def close(self) -> None:
        self._cancel_tick()
        _forget(self._app, self._surface_id, self)
        try:
            self.window.destroy()
        except Exception:
            pass

    def _tick(self) -> None:
        if self._finished:
            return
        self.detail_label.configure(text=self._running_detail())
        scheduler = getattr(self.window, "after", None)
        if callable(scheduler):
            self._after_id = scheduler(1000, self._tick)

    def _running_detail(self) -> str:
        elapsed = int(monotonic() - self._started_monotonic)
        return f"Status: running\nProgress: in progress\nRuntime: {format_duration(elapsed)}"

    def _close_if_finished(self) -> None:
        if self._finished:
            self.close()

    def _cancel_tick(self) -> None:
        if self._after_id is None:
            return
        try:
            self.window.after_cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None

    def _stop_progress(self) -> None:
        try:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(1)
        except Exception:
            pass


def start(app, surface_id: str, action_link: dict, payload: dict | None = None) -> OperationProgressWindow | None:
    del payload
    if not should_show(action_link) or not _has_window(app):
        return None
    windows = _windows(app)
    previous = windows.get(surface_id)
    if isinstance(previous, OperationProgressWindow):
        previous.close()
    title = str(action_link.get("progress_title") or action_link.get("label") or action_link.get("action") or "Operation")
    status = str(action_link.get("progress_status") or f"{title} has started.")
    warning = str(action_link.get("progress_warning") or "").strip()
    handle = OperationProgressWindow(app, surface_id=surface_id, title=title, status=status, warning=warning)
    windows[surface_id] = handle
    return handle


def finish(handle: OperationProgressWindow | None, response: dict[str, Any], error: Exception | None = None) -> None:
    if handle is None:
        return
    if error is not None:
        handle.fail(str(error))
        return
    handle.complete(response)


def _windows(app) -> dict[str, OperationProgressWindow]:
    state = object.__getattribute__(app, "__dict__")
    windows = state.get("_operation_progress_windows")
    if isinstance(windows, dict):
        return windows
    windows = {}
    state["_operation_progress_windows"] = windows
    return windows


def _forget(app, surface_id: str, handle: OperationProgressWindow) -> None:
    windows = _windows(app)
    if windows.get(surface_id) is handle:
        windows.pop(surface_id, None)


def _has_window(app) -> bool:
    try:
        state = object.__getattribute__(app, "__dict__")
    except AttributeError:
        return False
    return bool(state.get("tk")) and callable(getattr(app, "after", None))
