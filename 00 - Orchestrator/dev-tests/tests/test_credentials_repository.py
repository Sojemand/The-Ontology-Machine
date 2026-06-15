from __future__ import annotations

import json

from orchestrator import credentials
from orchestrator.credentials import oauth_report
from orchestrator.credentials.types import CredentialsState
from orchestrator.models import UiState
from orchestrator.state import save_ui_state


def _identity_dpapi(monkeypatch) -> None:
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_available", lambda: True)
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_encrypt", lambda data: data)
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_decrypt", lambda data: data)


def test_credentials_state_roundtrip_uses_non_sensitive_json_only(tmp_path) -> None:
    state_dir = tmp_path / "state"
    state = CredentialsState(auth_mode="oauth")
    state.targets["llm_shared"].has_secret = True
    state.oauth_session.status = "connected"
    state.oauth_session.account_label = "OpenAI Account dfaefa67...4d0c"
    state.oauth_session.status_message = "OpenAI OAuth ist im Orchestrator aktiv."
    state.oauth_session.client_id_hint = "app_...rann"
    state.oauth_session.scope = "openid profile email offline_access"
    state.oauth_session.expires_at = "2026-04-04T09:26:27+00:00"
    state.oauth_session.account_id = "dfaefa67-27d0-4c61-bcfc-92cf67404d0c"
    state.oauth_session.has_refresh_token = True

    credentials.save_credentials_state(state_dir, state)

    loaded = credentials.load_credentials_state(state_dir)
    payload = json.loads((state_dir / "credentials_state.json").read_text(encoding="utf-8"))

    assert payload == {
        "targets": {
            "llm_shared": {"has_secret": True},
            "optimizer_ocr": {"has_secret": False},
            "embeddings": {"has_secret": False},
        },
        "oauth_session": {
            "status": "connected",
            "account_label": "OpenAI Account dfaefa67...4d0c",
            "status_message": "OpenAI OAuth ist im Orchestrator aktiv.",
            "client_id_hint": "app_...rann",
            "scope": "openid profile email offline_access",
            "expires_at": "2026-04-04T09:26:27+00:00",
            "account_id": "dfaefa67-27d0-4c61-bcfc-92cf67404d0c",
            "has_refresh_token": True,
        },
    }


def test_credentials_state_loader_accepts_legacy_auth_mode_field(tmp_path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "credentials_state.json").write_text(
        json.dumps(
            {
                "auth_mode": "oauth",
                "targets": {
                    "llm_shared": {"has_secret": True},
                    "embeddings": {"has_secret": False},
                },
                "oauth_session": {
                    "status": "connected",
                    "account_label": "",
                    "status_message": "",
                    "client_id_hint": "",
                    "scope": "",
                    "expires_at": "",
                    "account_id": "",
                    "has_refresh_token": False,
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = credentials.load_credentials_state(state_dir)

    assert loaded.auth_mode == "oauth"
    assert loaded.targets["llm_shared"].has_secret is True


def test_ui_state_json_remains_credentials_free(tmp_path) -> None:
    path = tmp_path / "ui_state.json"
    save_ui_state(
        path,
        UiState(
            input_folder="input",
            artifact_folder="artifacts",
            semantic_release_path="release.json",
            corpus_output_folder="corpus",
            mode="single",
        ),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert set(payload) == {
        "input_folder",
        "artifact_folder",
        "semantic_release_path",
        "corpus_output_folder",
        "selected_corpus_db_path",
        "semantic_release_mode",
        "new_database_name",
        "new_database_bootstrap_mode",
        "new_database_taxonomy_locale",
        "mode",
    }


def test_plaintext_state_json_never_contains_secret_values(tmp_path, monkeypatch) -> None:
    _identity_dpapi(monkeypatch)
    state_dir = tmp_path / "state"
    raw_secret = "super-secret"
    embed_secret = "embed-secret"

    credentials.save_api_key(state_dir, "llm_shared", raw_secret)
    credentials.save_api_key(state_dir, "embeddings", embed_secret)
    save_ui_state(state_dir / "ui_state.json", UiState(input_folder="input", artifact_folder="artifacts", corpus_output_folder="corpus"))

    assert raw_secret not in (state_dir / "credentials_state.json").read_text(encoding="utf-8")
    assert embed_secret not in (state_dir / "credentials_state.json").read_text(encoding="utf-8")
    assert raw_secret not in (state_dir / "ui_state.json").read_text(encoding="utf-8")
    assert embed_secret not in (state_dir / "ui_state.json").read_text(encoding="utf-8")
    assert raw_secret not in (state_dir / "keystore.enc").read_text(encoding="utf-8")
    assert embed_secret not in (state_dir / "keystore.enc").read_text(encoding="utf-8")


def test_oauth_report_redacts_token_values(tmp_path) -> None:
    state_dir = tmp_path / "state"
    oauth_report.write_oauth_report(
        state_dir,
        {
            "oauth": {
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "id_token": "id-secret",
                "token": {"access_token": "access-secret"},
            }
        },
    )

    payload = json.loads((state_dir / "oauth_latest_report.json").read_text(encoding="utf-8"))
    text = (state_dir / "oauth_latest_report.json").read_text(encoding="utf-8")

    assert payload["oauth"]["access_token"] == "[REDACTED]"
    assert payload["oauth"]["refresh_token"] == "[REDACTED]"
    assert payload["oauth"]["id_token"] == "[REDACTED]"
    assert "access-secret" not in text
    assert "refresh-secret" not in text
    assert "id-secret" not in text
