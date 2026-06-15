from __future__ import annotations

import hashlib
import json


def _require_phase19_owner_envelope(payload: dict, owner_action: str) -> None:
    if payload.get("schema_version") != "kernel.pipeline_owner_request.v1":
        raise ValueError("schema_version must be kernel.pipeline_owner_request.v1.")
    if payload.get("owner_action") != owner_action:
        raise ValueError(f"owner_action must be {owner_action}.")
    for key in ("workflow_run_id", "adapter_call_id", "requested_at", "request_fingerprint"):
        _required_text(payload, key)
    if not isinstance(payload.get("target_identity"), dict):
        raise ValueError("target_identity must be an object.")
    if str(payload.get("request_fingerprint") or "") != _request_fingerprint(payload):
        raise ValueError("request_fingerprint does not match payload.")


def _required_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} fehlt oder ist ungueltig.")
    return value.strip()


def _request_fingerprint(payload: dict) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
