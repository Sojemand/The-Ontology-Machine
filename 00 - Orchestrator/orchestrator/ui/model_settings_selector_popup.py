"""Popup behavior for the Orchestrator model selector widget."""

from __future__ import annotations

from . import theme
from .model_settings_widget_utils import (
    bind_listbox_wheel,
    bind_popup_focus,
    focus_widget,
    widget_exists,
)


def _ctk():
    from . import model_settings_widgets

    return model_settings_widgets.ctk


def _tk():
    from . import model_settings_widgets

    return model_settings_widgets.tk


class ScrollableModelSelectorPopupMixin:
    def _open_popup(self) -> None:
        if self._popup is not None:
            self._close_popup()
            return
        ctk = _ctk()
        tk = _tk()
        popup_cls = getattr(ctk, "CTkToplevel", None)
        if popup_cls is None:
            return
        popup = popup_cls(self._container)
        self._popup = popup
        self._popup_sync_token += 1
        self._cancel_popup_sync()
        if hasattr(popup, "overrideredirect"):
            popup.overrideredirect(True)
        if hasattr(popup, "attributes"):
            try:
                popup.attributes("-topmost", True)
            except Exception:
                pass
        self._update_popup_geometry()
        popup.bind("<Destroy>", lambda _event: self._on_popup_destroy(popup))
        popup.bind("<Escape>", lambda _event: self._close_popup())
        surface = ctk.CTkFrame(popup)
        surface.pack(fill="both", expand=True)
        list_frame = ctk.CTkFrame(surface, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(
            list_frame,
            activestyle="none",
            borderwidth=0,
            exportselection=False,
            font=theme.font_normal(),
            highlightthickness=0,
            relief="flat",
            selectmode="browse",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.configure(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        self._popup_focus_target = listbox
        self._populate_listbox(listbox)
        listbox.bind("<ButtonRelease-1>", lambda _event: self._choose_from_listbox(listbox))
        listbox.bind("<Double-Button-1>", lambda _event: self._choose_from_listbox(listbox))
        listbox.bind("<Return>", lambda _event: self._choose_from_listbox(listbox))
        for widget in (listbox, scrollbar):
            bind_listbox_wheel(widget, listbox)
        for widget in (listbox, scrollbar, list_frame, surface, popup):
            bind_popup_focus(widget, listbox)
        if hasattr(popup, "lift"):
            popup.lift()
        focus_widget(listbox)
        self._schedule_popup_sync(self._popup_sync_token)

    def _populate_listbox(self, listbox) -> None:
        if self._values:
            for value in self._values:
                listbox.insert("end", value)
            return
        listbox.insert("end", "No models loaded for the currently selected provider.")
        listbox.configure(state="disabled")

    def _close_popup(self) -> None:
        popup = self._popup
        self._popup = None
        self._popup_focus_target = None
        self._popup_sync_token += 1
        self._cancel_popup_sync()
        if popup is None:
            return
        try:
            exists = bool(getattr(popup, "winfo_exists", lambda: True)())
        except Exception:
            exists = False
        if exists:
            try:
                popup.destroy()
            except Exception:
                pass

    def _schedule_popup_sync(self, token: int) -> None:
        popup = self._popup
        if popup is None or token != self._popup_sync_token:
            return
        if hasattr(popup, "after"):
            self._popup_after_id = popup.after(75, lambda: self._run_popup_sync(token))

    def _run_popup_sync(self, token: int) -> None:
        try:
            self._sync_popup_position(token)
        except Exception:
            self._close_popup()

    def _sync_popup_position(self, token: int) -> None:
        self._popup_after_id = None
        popup = self._popup
        if popup is None or token != self._popup_sync_token:
            return
        if not widget_exists(self._container) or not widget_exists(popup):
            self._close_popup()
            return
        self._update_popup_geometry()
        self._schedule_popup_sync(token)

    def _cancel_popup_sync(self) -> None:
        popup = self._popup
        after_cancel = getattr(popup, "after_cancel", None)
        if self._popup_after_id is not None and callable(after_cancel):
            try:
                after_cancel(self._popup_after_id)
            except Exception:
                pass
        self._popup_after_id = None

    def _on_popup_destroy(self, popup) -> None:
        if popup is self._popup:
            self._popup = None
            self._popup_focus_target = None
        self._cancel_popup_sync()

    def _update_popup_geometry(self) -> None:
        popup = self._popup
        if popup is None or not hasattr(popup, "geometry"):
            return
        if not widget_exists(popup) or not widget_exists(self._container):
            self._close_popup()
            return
        root_x = getattr(self._container, "winfo_rootx", lambda: 0)()
        root_y = getattr(self._container, "winfo_rooty", lambda: 0)()
        width = max(int(getattr(self._container, "winfo_width", lambda: 360)() or 360), 320)
        height = self._popup_height()
        container_height = int(getattr(self._container, "winfo_height", lambda: theme.INPUT_HEIGHT)())
        popup.geometry(f"{width}x{height}+{root_x}+{root_y + container_height}")

    def _popup_height(self) -> int:
        visible_rows = min(max(len(self._values), 1), 10)
        return (visible_rows * 30) + 24

    def _choose_from_listbox(self, listbox) -> str:
        selection = getattr(listbox, "curselection", lambda: ())()
        if not selection:
            return "break"
        index = selection[0]
        value = str(getattr(listbox, "get", lambda _index: "")(index) or "").strip()
        if not value or value.startswith("No models"):
            return "break"
        self._choose(value)
        return "break"
