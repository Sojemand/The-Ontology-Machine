from __future__ import annotations

from orchestrator import credentials
from orchestrator.credentials.types import CredentialsState
from orchestrator.ui import credentials_rendering, layout

from .credentials_ui_support import _make_app, _token, install_fake_ctk


def test_credentials_view_shows_auto_fallback_and_keeps_llm_key_editable(monkeypatch, tmp_path) -> None:
    install_fake_ctk(monkeypatch)
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": False, "optimizer_ocr": False, "embeddings": False}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: _token())

    state_dir = tmp_path / "state"
    credentials.save_credentials_state(state_dir, CredentialsState())
    app = _make_app(tmp_path)
    layout.build_ui(app)
    app._tabs.set("Credentials")
    app._credentials_state = credentials.load_credentials_state(state_dir)
    app._credentials_profile = credentials.resolve_credentials(state_dir)

    credentials_rendering.apply_credentials_view(app)

    corpus = app._capability_widgets[("corpus_builder", "generate_embeddings")]
    llm_widgets = app._credential_widgets["llm_shared"]
    embeddings_widgets = app._credential_widgets["embeddings"]

    assert corpus["status"].cget("text") == "Warning"
    assert "skips embeddings" in corpus["detail"].cget("text")
    assert app._oauth_status_label.cget("text") == "Status: Connected"
    assert app._credentials_mode_label.cget("text") == "OpenAI OAuth active"
    assert llm_widgets["presence"].cget("text") == "No key for selected provider"
    assert (llm_widgets["entry"].cget("state"), llm_widgets["save"].cget("state"), embeddings_widgets["entry"].cget("state")) == ("normal", "normal", "normal")
    assert app._credentials_notice_label.cget("text")


def test_credentials_secret_entries_bind_context_paste(monkeypatch, tmp_path) -> None:
    install_fake_ctk(monkeypatch)

    app = _make_app(tmp_path)
    layout.build_ui(app)
    app._tabs.set("Credentials")

    for widgets in app._credential_widgets.values():
        assert "<Button-3>" in widgets["entry"]._bindings
        assert "<Button-2>" in widgets["entry"]._bindings
