from __future__ import annotations

from types import SimpleNamespace

from cases.credentials_ui_cases import _fake_ctk
from .model_settings_layout_support import PopupStub, TkListboxStub, TkScrollbarStub
from orchestrator.ui import model_settings_layout


def test_scrollable_model_selector_does_not_close_itself_on_focusout(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    fake_ctk.CTkToplevel = PopupStub
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)
    monkeypatch.setattr(model_settings_layout, "tk", SimpleNamespace(Listbox=TkListboxStub, Scrollbar=TkScrollbarStub))

    selector = model_settings_layout._ScrollableModelSelector(object(), values=["openai/gpt-5.4"])
    selector._open_popup()

    assert selector._popup is not None
    assert "<Escape>" in selector._popup.bindings
    assert "<FocusOut>" not in selector._popup.bindings


def test_scrollable_model_selector_focuses_popup_scroll_target(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    fake_ctk.CTkToplevel = PopupStub
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)
    monkeypatch.setattr(model_settings_layout, "tk", SimpleNamespace(Listbox=TkListboxStub, Scrollbar=TkScrollbarStub))

    selector = model_settings_layout._ScrollableModelSelector(object(), values=["openai/gpt-5.4"])
    selector._open_popup()

    assert selector._popup is not None
    assert selector._popup_focus_target is not None
    assert selector._popup_focus_target.focus_calls == 1


def test_scroll_listbox_wheel_returns_break_and_scrolls_list(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)
    listbox = TkListboxStub()

    result = model_settings_layout._scroll_listbox_wheel(listbox, SimpleNamespace(delta=-120, num=0))

    assert result == "break"
    assert listbox.scroll_calls == [(1, "units")]


def test_scroll_listbox_wheel_ignores_non_numeric_button_value(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)
    listbox = TkListboxStub()

    result = model_settings_layout._scroll_listbox_wheel(listbox, SimpleNamespace(delta=-120, num="??"))

    assert result == "break"
    assert listbox.scroll_calls == [(1, "units")]
