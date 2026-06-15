from __future__ import annotations

import json
from pathlib import Path

import orchestrator.admin_contract as admin_contract
from orchestrator.models import RuntimeSettingsState


def _run_contract(tmp_path: Path, payload: dict) -> dict:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = admin_contract.main(["--request", str(request_path), "--response", str(response_path)])
    assert exit_code == 0
    return json.loads(response_path.read_text(encoding="utf-8"))


def test_manage_runtime_settings_writes_owner_state(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(admin_contract, "ORCHESTRATOR_ROOT", tmp_path)
    settings = RuntimeSettingsState().to_dict()
    settings["normalizer"]["model"] = "gpt-5.4"

    payload = _run_contract(
        tmp_path,
        {"action": "manage_runtime_settings", "operation": "write", "settings": settings},
    )

    assert payload["status"] == "ok"
    persisted = json.loads((tmp_path / "state" / "runtime_settings.json").read_text(encoding="utf-8"))
    assert persisted["normalizer"]["model"] == "gpt-5.4"


def test_manage_credentials_delegates_to_credentials_owner(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(admin_contract, "ORCHESTRATOR_ROOT", tmp_path)
    calls: list[tuple[str, str]] = []

    def fake_save(_state_dir, target, value, *, provider_settings=None):
        del provider_settings
        calls.append((target, value))
        return type("State", (), {"to_dict": lambda self: {"targets": {target: {"has_secret": True}}}})()

    monkeypatch.setattr(admin_contract.workflow.credentials, "save_api_key", fake_save)

    payload = _run_contract(
        tmp_path,
        {
            "action": "manage_credentials",
            "operation": "set_api_key",
            "target": "llm_shared",
            "secret_value": "sk-test",
        },
    )

    assert payload["status"] == "ok"
    assert calls == [("llm_shared", "sk-test")]


def test_reveal_secret_requires_unlock_and_audits(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(admin_contract, "ORCHESTRATOR_ROOT", tmp_path)
    monkeypatch.setattr(admin_contract.workflow.credentials, "load_api_key", lambda *_args, **_kwargs: "sk-visible")

    payload = _run_contract(
        tmp_path,
        {
            "action": "reveal_secret",
            "target": "llm_shared",
            "purpose": "operator-request",
            "unlock_phrase": "REVEAL_SECRET:llm_shared",
        },
    )

    assert payload == {"status": "ok", "target": "llm_shared", "secret_value": "sk-visible"}
    audit = (tmp_path / "state" / "admin_audit.jsonl").read_text(encoding="utf-8")
    assert "reveal_secret" in audit
    assert "sk-visible" not in audit


def test_reveal_secret_rejects_missing_unlock(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(admin_contract, "ORCHESTRATOR_ROOT", tmp_path)

    payload = _run_contract(
        tmp_path,
        {
            "action": "reveal_secret",
            "target": "llm_shared",
            "purpose": "operator-request",
            "unlock_phrase": "wrong",
        },
    )

    assert payload["status"] == "error"
    assert "unlock_phrase" in payload["reason"]
