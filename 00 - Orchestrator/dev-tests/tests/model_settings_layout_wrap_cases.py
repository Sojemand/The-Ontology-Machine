from __future__ import annotations

from types import SimpleNamespace

from cases.credentials_ui_cases import _fake_ctk
from .model_settings_layout_support import AfterTextboxStub, MeasuredTextboxStub
from orchestrator.ui import model_settings_layout, responsive


def test_wrap_label_uses_selectable_text_proxy_and_stays_configurable(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)

    app = SimpleNamespace(_model_wrap_labels=[])
    label = model_settings_layout._wrap_label(app, object(), "Starttext")

    assert label.cget("text") == "Starttext"

    label.configure(text="Aktualisiert", text_color="orange")
    responsive.set_wrap(label, 280)

    assert label.cget("text") == "Aktualisiert"
    assert label.cget("text_color") == "orange"
    assert label.cget("wraplength") == 280
    assert app._model_wrap_labels == [label]


def test_wrap_label_uses_measured_textbox_height_when_available(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    fake_ctk.CTkTextbox = MeasuredTextboxStub
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)

    app = SimpleNamespace(_model_wrap_labels=[])
    label = model_settings_layout._wrap_label(app, object(), "Mehrzeiliger Modellhinweis")

    assert label.cget("height") == 62
    assert label.cget("width") == 332


def test_wrap_label_ignores_updates_after_destroy(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    fake_ctk.CTkTextbox = AfterTextboxStub
    monkeypatch.setattr(model_settings_layout, "ctk", fake_ctk)

    app = SimpleNamespace(_model_wrap_labels=[])
    label = model_settings_layout._wrap_label(app, object(), "Crashschutz")
    initial_calls = len(label.configure_calls)

    label._bindings["<Destroy>"](None)
    label.configure(text="Spaeteres Update", wraplength=420)

    assert label.cget("text") == "Spaeteres Update"
    assert len(label.configure_calls) == initial_calls
