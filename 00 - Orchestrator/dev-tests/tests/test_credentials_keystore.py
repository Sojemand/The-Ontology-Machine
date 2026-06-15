from __future__ import annotations

import json

from orchestrator import credentials
from orchestrator.models import ProviderEndpointSettings


def test_keystore_save_load_delete_and_probe_are_local_to_state_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_available", lambda: True)
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_encrypt", lambda data: data[::-1])
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_decrypt", lambda data: data[::-1])

    state_dir = tmp_path / "state"

    assert credentials.has_api_key(state_dir, "llm_shared") is False

    credentials.save_api_key(state_dir, "llm_shared", "first-secret")
    credentials.save_api_key(state_dir, "optimizer_ocr", "ocr-secret")
    credentials.save_api_key(state_dir, "embeddings", "second-secret")

    assert credentials.has_api_key(state_dir, "llm_shared") is True
    assert credentials.has_api_key(state_dir, "optimizer_ocr") is True
    assert credentials.has_api_key(state_dir, "embeddings") is True
    assert credentials.load_api_key(state_dir, "llm_shared") == "first-secret"
    assert credentials.load_api_key(state_dir, "optimizer_ocr") == "ocr-secret"
    assert credentials.load_api_key(state_dir, "embeddings") == "second-secret"

    store = json.loads((state_dir / "keystore.enc").read_text(encoding="utf-8"))
    assert set(store) == {"openai.llm_shared.api_key", "openai.optimizer_ocr.api_key", "openai.embeddings.api_key"}
    assert (state_dir / "keystore.lock").exists()

    assert credentials.delete_api_key(state_dir, "llm_shared") is not None
    assert credentials.has_api_key(state_dir, "llm_shared") is False
    assert credentials.load_api_key(state_dir, "llm_shared") is None


def test_keystore_ignores_stale_lock_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_available", lambda: True)
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_encrypt", lambda data: data[::-1])
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_decrypt", lambda data: data[::-1])

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "keystore.lock").write_text("stale-pid", encoding="utf-8")

    credentials.save_api_key(state_dir, "llm_shared", "fresh-secret")

    assert credentials.load_api_key(state_dir, "llm_shared") == "fresh-secret"


def test_keystore_returns_none_for_load_when_dpapi_is_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_available", lambda: False)

    assert credentials.load_api_key(tmp_path / "state", "llm_shared") is None


def test_keystore_scopes_keys_per_provider_and_does_not_reuse_openai_legacy_for_xai(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_available", lambda: True)
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_encrypt", lambda data: data[::-1])
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_decrypt", lambda data: data[::-1])

    state_dir = tmp_path / "state"
    openai = ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1")
    xai = ProviderEndpointSettings(provider_id="xai", base_url="https://api.x.ai/v1")

    credentials.save_api_key(state_dir, "llm_shared", "openai-secret")

    assert credentials.load_api_key(state_dir, "llm_shared", provider_settings=openai) == "openai-secret"
    assert credentials.load_api_key(state_dir, "llm_shared", provider_settings=xai) is None

    credentials.save_api_key(state_dir, "llm_shared", "xai-secret", provider_settings=xai)

    assert credentials.load_api_key(state_dir, "llm_shared", provider_settings=xai) == "xai-secret"


def test_provider_specific_save_syncs_secret_state_before_runtime_file_catches_up(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_available", lambda: True)
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_encrypt", lambda data: data[::-1])
    monkeypatch.setattr("orchestrator.credentials.keystore._dpapi_decrypt", lambda data: data[::-1])

    state_dir = tmp_path / "state"
    openai = ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1")
    openrouter = ProviderEndpointSettings(provider_id="openrouter", base_url="https://openrouter.ai/api/v1")

    saved = credentials.save_api_key(
        state_dir,
        "llm_shared",
        "openrouter-secret",
        provider_settings=openrouter,
    )

    assert saved.targets["llm_shared"].has_secret is True
    assert credentials.load_credentials_state(state_dir).targets["llm_shared"].has_secret is True
    assert credentials.load_api_key(state_dir, "llm_shared", provider_settings=openrouter) == "openrouter-secret"
    assert credentials.load_api_key(state_dir, "llm_shared", provider_settings=openai) is None

    deleted = credentials.delete_api_key(state_dir, "llm_shared", provider_settings=openrouter)

    assert deleted.targets["llm_shared"].has_secret is False
    assert credentials.load_credentials_state(state_dir).targets["llm_shared"].has_secret is False
