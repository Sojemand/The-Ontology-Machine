"""Scrollable model selector widget for the Orchestrator model settings UI."""

from __future__ import annotations

from . import theme
from .model_settings_selector_popup import ScrollableModelSelectorPopupMixin


def _ctk():
    from . import model_settings_widgets

    return model_settings_widgets.ctk


class ScrollableModelSelector(ScrollableModelSelectorPopupMixin):
    def __init__(self, parent, *, values: list[str] | None = None, command=None) -> None:
        ctk = _ctk()
        self._values = list(values or [])
        self._command = command
        self._popup = None
        self._popup_focus_target = None
        self._popup_sync_token = 0
        self._popup_after_id = None
        self._container = ctk.CTkFrame(parent, fg_color="transparent")
        self._container.bind("<Destroy>", lambda _event: self._close_popup())
        self._entry = ctk.CTkEntry(self._container, height=theme.INPUT_HEIGHT)
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._button = ctk.CTkButton(
            self._container,
            text="v",
            width=40,
            height=theme.INPUT_HEIGHT,
            command=self._open_popup,
        )
        self._button.pack(side="right")

    def pack(self, *args, **kwargs):
        return self._container.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        return self._container.grid(*args, **kwargs)

    def bind(self, sequence, callback):
        self._entry.bind(sequence, callback)

    def configure(self, **kwargs):
        if "values" in kwargs:
            self._values = list(kwargs.pop("values") or [])
            self._close_popup()
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._entry.configure(state=state)
            self._button.configure(state=state)
        if kwargs:
            self._entry.configure(**kwargs)

    def cget(self, key):
        if key == "values":
            return list(self._values)
        return self._entry.cget(key)

    def get(self) -> str:
        return str(self._entry.get() or "")

    def set(self, value: str) -> None:
        self.delete(0, "end")
        if value:
            self.insert(0, value)

    def delete(self, *args) -> None:
        self._entry.delete(*args)

    def insert(self, *args) -> None:
        self._entry.insert(*args)

    def __getattr__(self, name: str):
        return getattr(self._container, name)

    def _choose(self, value: str) -> None:
        self.set(value)
        self._close_popup()
        if callable(self._command):
            self._command(value)
