"""Owner-local admin workflows for runtime settings and credentials."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import credentials
from ..models import RuntimeSettingsState
from ..state import load_runtime_settings, save_runtime_settings


def error_response(message: str) -> dict[str, Any]:
    return {"status": "error", "reason": str(message)}


def inspect_runtime(*, root: Path) -> dict[str, Any]:
    state_dir = _state_dir(root)
    return {
        "status": "ok",
        "runtime_settings": load_runtime_settings(state_dir).to_dict(),
        "credentials": _credentials_summary(state_dir),
    }


def manage_runtime_settings(command: dict[str, Any], *, root: Path) -> dict[str, Any]:
    state_dir = _state_dir(root)
    operation = command["operation"]
    previous = load_runtime_settings(state_dir).to_dict()
    if operation == "read":
        return {"status": "ok", "operation": operation, "runtime_settings": previous}
    if operation == "reset":
        state = RuntimeSettingsState()
    else:
        state = RuntimeSettingsState.from_dict(command["settings"])
    save_runtime_settings(state_dir, state)
    return {
        "status": "ok",
        "operation": operation,
        "runtime_settings": state.to_dict(),
        "previous_runtime_settings": previous,
    }


def manage_credentials(command: dict[str, Any], *, root: Path) -> dict[str, Any]:
    state_dir = _state_dir(root)
    operation = command["operation"]
    if operation == "inspect":
        return {"status": "ok", "operation": operation, "credentials": _credentials_summary(state_dir)}
    target = command["target"]
    provider = load_runtime_settings(state_dir).provider_settings_for_target(target)
    if operation == "set_api_key":
        state = credentials.save_api_key(
            state_dir,
            target,
            command["secret_value"],
            provider_settings=provider,
        )
        _audit(state_dir, "manage_credentials", target, detail="set_api_key")
        return {"status": "ok", "operation": operation, "target": target, "state": state.to_dict()}
    state = credentials.delete_api_key(state_dir, target, provider_settings=provider)
    _audit(state_dir, "manage_credentials", target, detail="delete_api_key")
    return {"status": "ok", "operation": operation, "target": target, "state": state.to_dict()}


def reveal_secret(command: dict[str, str], *, root: Path) -> dict[str, Any]:
    state_dir = _state_dir(root)
    target = command["target"]
    provider = load_runtime_settings(state_dir).provider_settings_for_target(target)
    value = credentials.load_api_key(state_dir, target, provider_settings=provider)
    if value is None:
        return error_response(f"Kein Secret fuer {target} vorhanden.")
    _audit(state_dir, "reveal_secret", target, detail=command["purpose"])
    return {"status": "ok", "target": target, "secret_value": value}


def _credentials_summary(state_dir: Path) -> dict[str, Any]:
    profile = credentials.resolve_credentials(state_dir)
    return {
        "auth_mode": profile.auth_mode,
        "oauth_session": profile.oauth_session.to_dict(),
        "target_presence": dict(profile.target_presence),
        "target_readiness": dict(profile.target_readiness),
        "target_sources": dict(profile.target_sources),
        "target_messages": dict(profile.target_messages),
        "capabilities": [
            {
                "module_key": item.module_key,
                "operation": item.operation,
                "credential_target": item.credential_target,
                "supported": item.supported,
                "ready": item.ready,
                "warning_only": item.warning_only,
                "source": item.source,
                "block_reasons": list(item.block_reasons),
            }
            for item in profile.capabilities
        ],
    }


def _audit(state_dir: Path, action: str, target: str, *, detail: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "detail": detail,
    }
    with (state_dir / "admin_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _state_dir(root: Path) -> Path:
    path = Path(root) / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = [
    "error_response",
    "inspect_runtime",
    "manage_credentials",
    "manage_runtime_settings",
    "reveal_secret",
]
