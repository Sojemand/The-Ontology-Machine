from __future__ import annotations

from types import SimpleNamespace

from orchestrator.credentials.oauth_types import OAuthTokenBundle
from orchestrator.credentials.types import CredentialsState
from orchestrator.models import RuntimeSettingsState
from orchestrator.ui import credentials_layout, debug_controls_layout, debug_layout, debug_monitor_layout, debug_results_layout, layout, model_settings_layout, responsive, status_control_cards, status_layout


class _Widget:
    def __init__(self, *args, **kwargs) -> None:
        self._value = kwargs.get("text", "")
        self._config = dict(kwargs)
        self._children: list[object] = []
        self._bindings: dict[str, object] = {}

    def pack(self, *args, **kwargs):
        return None

    def pack_forget(self):
        return None

    def grid(self, *args, **kwargs):
        return None

    def grid_forget(self, *args, **kwargs):
        return None

    def grid_columnconfigure(self, *args, **kwargs):
        return None

    def winfo_children(self):
        return list(self._children)

    def winfo_width(self):
        return 1280

    def bind(self, *args, **kwargs):
        if len(args) >= 2:
            self._bindings[args[0]] = args[1]
        return None

    def insert(self, *args, **kwargs):
        self._value = args[-1] if args else ""

    def delete(self, *args, **kwargs):
        self._value = ""

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def configure(self, **kwargs):
        self._config.update(kwargs)
        if "text" in kwargs:
            self._value = kwargs["text"]

    def cget(self, key):
        return self._config.get(key, self._value if key == "text" else None)


class _Tabview(_Widget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tabs: list[str] = []
        self.current = ""
        self.command = kwargs.get("command")

    def add(self, name: str):
        self.tabs.append(name)
        return _Widget()

    def set(self, name: str):
        self.current = name
        if callable(self.command):
            self.command()

    def get(self):
        return self.current


class _Var:
    def __init__(self, value=None) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def _token() -> OAuthTokenBundle:
    return OAuthTokenBundle(
        access_token="access-token",
        refresh_token="refresh-token",
        id_token="id-token",
        token_type="Bearer",
        expires_at="2026-04-04T09:26:27+00:00",
        account_id="dfaefa67-27d0-4c61-bcfc-92cf67404d0c",
        client_id="app_EMoamEEZ73f0CkXaXp7hrann",
        session_id="authsess_demo",
        scope="openid profile email offline_access",
        token_status_code=200,
    )


def _fake_ctk():
    return SimpleNamespace(
        CTkFrame=_Widget,
        CTkButton=_Widget,
        CTkCheckBox=_Widget,
        CTkEntry=_Widget,
        CTkLabel=_Widget,
        CTkOptionMenu=_Widget,
        CTkProgressBar=_Widget,
        CTkScrollableFrame=_Widget,
        CTkSegmentedButton=_Widget,
        CTkTabview=_Tabview,
        CTkTextbox=_Widget,
        BooleanVar=_Var,
        StringVar=_Var,
    )


def _make_app(tmp_path):
    return SimpleNamespace(
        _credentials_state=CredentialsState(),
        _browse_input_folder=lambda: None,
        _browse_artifact_folder=lambda: None,
        _browse_release_file=lambda: None,
        _activate_selected_release=lambda: None,
        _browse_corpus_folder=lambda: None,
        _browse_database_file=lambda: None,
        _create_artifact_tree=lambda: None,
        _create_database=lambda: None,
        _open_edit_suite=lambda: None,
        _show_status_help=lambda: None,
        _start_processing=lambda: None,
        _start_embeddings=lambda: None,
        _reset_run_history=lambda: None,
        _abort_processing=lambda: None,
        _on_ui_change=lambda: None,
        _on_mode_change=lambda: None,
        _on_semantic_release_mode_change=lambda: None,
        _on_runtime_settings_change=lambda: None,
        _flush_pending_save=lambda _key: None,
        _flush_pending_saves=lambda: None,
        _save_credentials_target=lambda _target: None,
        _delete_credentials_target=lambda _target: None,
        _login_oauth=lambda: None,
        _logout_oauth=lambda: None,
        _runtime_settings=RuntimeSettingsState(),
        _update_button_state=lambda: None,
        _on_debug_change=lambda: None,
        _start_debug_session=lambda: None,
        _refresh_debug_session=lambda: None,
        _cancel_debug_session=lambda: None,
        _open_debug_artifacts=lambda: None,
        _reset_debug_output=lambda: None,
        _browse_debug_input=lambda: None,
        _browse_debug_source=lambda: None,
        _show_debug_help=lambda: None,
        _load_debug_artifact_file=lambda: None,
        _load_debug_artifact_dir=lambda: None,
        _clear_debug_artifact_import=lambda: None,
        _processing=False,
        bind=lambda *_args, **_kwargs: None,
        after=lambda _delay, callback: callback(),
        _state_dir=tmp_path / "state",
    )


def install_fake_ctk(monkeypatch):
    fake_ctk = _fake_ctk()
    for module in (
        layout,
        status_layout,
        credentials_layout,
        debug_layout,
        debug_controls_layout,
        debug_monitor_layout,
        debug_results_layout,
        model_settings_layout,
        responsive,
        status_control_cards,
    ):
        monkeypatch.setattr(module, "ctk", fake_ctk)
    return fake_ctk
