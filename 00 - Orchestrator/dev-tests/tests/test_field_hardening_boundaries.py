from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator.credentials import oauth_token_store
from orchestrator.credentials.oauth_types import OAuthTokenBundle
from orchestrator.pipeline import artifact_repository_files, success_publication


def _link_previous(path: Path) -> tuple[Path, str]:
    previous_text = path.read_text(encoding="utf-8")
    link_path = path.with_name(f"{path.name}.previous")
    try:
        os.link(path, link_path)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hardlinks are not available for this filesystem: {exc}")
    return link_path, previous_text


def _assert_replaced_without_mutating_previous(path: Path, link_path: Path, previous_text: str) -> None:
    assert link_path.read_text(encoding="utf-8") == previous_text
    assert path.read_text(encoding="utf-8") != previous_text
    try:
        assert not os.path.samefile(path, link_path)
    except OSError:
        pass
    assert not list(path.parent.glob(".*.tmp"))


def _token(access_token: str) -> OAuthTokenBundle:
    return OAuthTokenBundle(
        access_token=access_token,
        refresh_token=f"refresh-{access_token}",
        id_token="",
        token_type="Bearer",
        expires_at="2026-06-01T12:00:00+00:00",
        account_id="acct",
        client_id="client",
        session_id="session",
        scope="openid",
        token_status_code=200,
    )


def test_oauth_token_cache_ignores_stale_lock_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(oauth_token_store, "_dpapi_available", lambda: True)
    monkeypatch.setattr(oauth_token_store, "_dpapi_encrypt", lambda data: data)
    monkeypatch.setattr(oauth_token_store, "_dpapi_decrypt", lambda data: data)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    oauth_token_store.token_lock_path(state_dir).write_text("stale-pid", encoding="utf-8")

    oauth_token_store.save_token(state_dir, _token("fresh-access"))

    loaded = oauth_token_store.load_token(state_dir)
    assert loaded is not None
    assert loaded.access_token == "fresh-access"


def test_publish_file_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    engine = SimpleNamespace(_active_log_path=tmp_path / "run.log")
    source = tmp_path / "state" / "source.txt"
    target = tmp_path / "Documents" / "published.txt"
    source.parent.mkdir()
    target.parent.mkdir(parents=True)
    source.write_text("new artifact", encoding="utf-8")
    target.write_text("old artifact", encoding="utf-8")
    link_path, previous_text = _link_previous(target)

    error = success_publication.publish_file(
        engine,
        source,
        target,
        allowed_roots=(tmp_path.resolve(),),
        action="Publish",
        noun="artifact",
    )

    assert error == ""
    _assert_replaced_without_mutating_previous(target, link_path, previous_text)
    assert target.read_text(encoding="utf-8") == "new artifact"


def test_bundle_copy_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    engine = SimpleNamespace(_active_log_path=tmp_path / "run.log")
    source = tmp_path / "state" / "bundle.txt"
    target = tmp_path / "Documents" / "bundle.txt"
    source.parent.mkdir()
    target.parent.mkdir(parents=True)
    source.write_text("new bundle", encoding="utf-8")
    target.write_text("old bundle", encoding="utf-8")
    link_path, previous_text = _link_previous(target)

    artifact_repository_files.copy_if_exists(engine, source, target, allowed_roots=(tmp_path.resolve(),))

    _assert_replaced_without_mutating_previous(target, link_path, previous_text)
    assert target.read_text(encoding="utf-8") == "new bundle"
