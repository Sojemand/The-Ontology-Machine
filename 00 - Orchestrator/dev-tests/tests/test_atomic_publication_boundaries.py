from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator.credentials import oauth_report, oauth_token_store
from orchestrator.credentials.oauth_types import OAuthTokenBundle
from orchestrator.debug_host import polling
from orchestrator.integrations import adapter as integrations_adapter
from orchestrator.integrations.types import ExternalDependencyStatus, ModuleHealthStatus
from orchestrator.pipeline import health_workflow, release_workflow, request_enrichment_io
from orchestrator.pipeline_batches import manifest_repository


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


def test_oauth_token_cache_replaces_hardlinked_previous_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(oauth_token_store, "_dpapi_available", lambda: True)
    monkeypatch.setattr(oauth_token_store, "_dpapi_encrypt", lambda data: data)
    monkeypatch.setattr(oauth_token_store, "_dpapi_decrypt", lambda data: data)
    state_dir = tmp_path / "state"

    oauth_token_store.save_token(state_dir, _token("old-access"))
    path = oauth_token_store.token_cache_path(state_dir)
    link_path, previous_text = _link_previous(path)

    oauth_token_store.save_token(state_dir, _token("new-access"))

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)
    loaded = oauth_token_store.load_token(state_dir)
    assert loaded is not None
    assert loaded.access_token == "new-access"


def test_oauth_report_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"

    path = oauth_report.write_oauth_report(state_dir, {"oauth": {"access_token": "old-secret"}})
    link_path, previous_text = _link_previous(path)

    oauth_report.write_oauth_report(state_dir, {"oauth": {"access_token": "new-secret", "status": "ok"}})

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)
    assert "new-secret" not in path.read_text(encoding="utf-8")


def test_debug_host_json_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"

    polling.write_json(path, {"status": "old"})
    link_path, previous_text = _link_previous(path)

    polling.write_json(path, {"status": "new"})

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)
    assert polling.load_snapshot(path).status == "new"


def test_contract_request_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "request.json"

    integrations_adapter._write_contract_request(path, {"action": "old"})
    link_path, previous_text = _link_previous(path)

    integrations_adapter._write_contract_request(path, {"action": "new"})

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)


def test_pipeline_batch_manifest_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"

    manifest_repository.write_json(path, {"status": "old"})
    link_path, previous_text = _link_previous(path)

    manifest_repository.write_json(path, {"status": "new"})

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)
    assert manifest_repository.read_json(path)["status"] == "new"


def test_request_enrichment_json_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "interpreter.request.json"

    request_enrichment_io.write_request_json(path, {"request": "old"})
    link_path, previous_text = _link_previous(path)

    request_enrichment_io.write_request_json(path, {"request": "new"})

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)
    assert request_enrichment_io.load_json_object(path, error_prefix="request")["request"] == "new"


def test_healthcheck_failure_artifact_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    artifact_path = run_dir / "healthcheck.failure.json"
    engine = SimpleNamespace(_active_log_path=run_dir / "run.log")
    old_result = ModuleHealthStatus(key="optimizer", display_name="Optimizer", healthy=False, message="old")
    new_result = ModuleHealthStatus(
        key="optimizer",
        display_name="Optimizer",
        healthy=False,
        message="new",
        dependencies=[ExternalDependencyStatus(name="ocr", required=True, healthy=False, detail="new")],
    )

    health_workflow._write_healthcheck_failure_artifact(
        engine,
        scope="run",
        results=[old_result],
        required_dependencies_by_module=None,
    )
    link_path, previous_text = _link_previous(artifact_path)

    health_workflow._write_healthcheck_failure_artifact(
        engine,
        scope="run",
        results=[new_result],
        required_dependencies_by_module={"optimizer": ("ocr",)},
    )

    _assert_replaced_without_mutating_previous(artifact_path, link_path, previous_text)
    assert "new" in artifact_path.read_text(encoding="utf-8")


def test_release_confirmation_artifact_replaces_hardlinked_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "release_activation.confirmation.json"

    release_workflow._write_confirmation_artifact(tmp_path, {"status": "old"})
    link_path, previous_text = _link_previous(path)

    release_workflow._write_confirmation_artifact(tmp_path, {"status": "new"})

    _assert_replaced_without_mutating_previous(path, link_path, previous_text)
    assert "new" in path.read_text(encoding="utf-8")
