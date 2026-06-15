from __future__ import annotations

from orchestrator import credentials
from orchestrator.credentials.oauth_types import OAuthTokenBundle
from orchestrator.credentials.types import CredentialsState


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


def _save_state(state_dir, *, auth_mode: str) -> None:
    credentials.save_credentials_state(state_dir, CredentialsState(auth_mode=auth_mode))


def test_api_keys_resolve_llm_shared_and_embeddings_separately(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="api_keys")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": True, "optimizer_ocr": False, "embeddings": False}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: None)

    profile = credentials.resolve_credentials(state_dir)

    assert profile.target_readiness["llm_shared"] is True
    assert profile.target_readiness["optimizer_ocr"] is False
    assert profile.target_readiness["embeddings"] is False
    assert profile.capability_for("interpreter").ready is True
    assert profile.capability_for("optimizer").ready is False
    assert profile.capability_for("corpus_builder", "generate_embeddings").ready is False


def test_missing_llm_key_blocks_only_llm_modules(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="api_keys")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": False, "optimizer_ocr": True, "embeddings": True}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: None)

    profile = credentials.resolve_credentials(state_dir)

    assert profile.capability_for("interpreter").ready is False
    assert profile.capability_for("interpreter").ready is False
    assert profile.capability_for("normalizer").ready is False
    assert profile.capability_for("optimizer").ready is True
    assert profile.capability_for("corpus_builder", "generate_embeddings").ready is True


def test_missing_optimizer_key_points_user_to_orchestrator_credentials(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="api_keys")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": True, "optimizer_ocr": False, "embeddings": True}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: None)

    profile = credentials.resolve_credentials(state_dir)
    optimizer = profile.capability_for("optimizer")

    assert optimizer.ready is False
    assert "Open the Orchestrator" in optimizer.block_reasons[0]
    assert "Optimizer OCR Provider credentials" in optimizer.block_reasons[0]
    assert "Kernel/Taxonomy workflow" in optimizer.block_reasons[0]
    assert "OpenAI" not in optimizer.block_reasons[0]


def test_missing_embeddings_key_is_warning_only(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="api_keys")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": True, "optimizer_ocr": True, "embeddings": False}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: None)

    profile = credentials.resolve_credentials(state_dir)
    corpus = profile.capability_for("corpus_builder", "generate_embeddings")

    assert profile.capability_for("interpreter").ready is True
    assert profile.capability_for("optimizer").ready is True
    assert corpus.ready is False
    assert corpus.warning_only is True
    assert "skips embeddings" in corpus.block_reasons[0]


def test_oauth_keeps_embeddings_separate_and_ready_for_llm_modules(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="oauth")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": False, "optimizer_ocr": False, "embeddings": False}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: _token())

    profile = credentials.resolve_credentials(state_dir)
    corpus = profile.capability_for("corpus_builder", "generate_embeddings")

    assert profile.auth_mode == "oauth"
    assert profile.oauth_session.status == "connected"
    assert profile.capability_for("interpreter").ready is True
    assert profile.capability_for("interpreter").ready is True
    assert profile.capability_for("normalizer").ready is True
    assert profile.capability_for("optimizer").ready is True
    assert corpus.ready is False
    assert corpus.warning_only is True
    assert "keystore.enc" in corpus.source


def test_oauth_uses_separate_embeddings_key_when_present(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="oauth")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": False, "optimizer_ocr": False, "embeddings": True}[target],
    )
    monkeypatch.setattr("orchestrator.credentials.oauth_token_store.load_token", lambda _state_dir: _token())

    profile = credentials.resolve_credentials(state_dir)

    assert profile.capability_for("interpreter").ready is True
    assert profile.capability_for("optimizer").ready is True
    assert profile.capability_for("corpus_builder", "generate_embeddings").ready is True


def test_oauth_error_falls_back_to_shared_llm_key_when_present(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    _save_state(state_dir, auth_mode="oauth")
    monkeypatch.setattr(
        "orchestrator.credentials.keystore.has_api_key",
        lambda _state_dir, target, **_kwargs: {"llm_shared": True, "optimizer_ocr": True, "embeddings": False}[target],
    )
    monkeypatch.setattr(
        "orchestrator.credentials.oauth_token_store.load_token",
        lambda _state_dir: None,
    )

    profile = credentials.resolve_credentials(state_dir)

    assert profile.auth_mode == "api_keys"
    assert profile.capability_for("interpreter").ready is True
    assert profile.capability_for("optimizer").ready is True

