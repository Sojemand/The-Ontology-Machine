from __future__ import annotations

from typing import Any


def installation_state_drift_reason(
    release: dict[str, Any] | None,
    installation_state: dict[str, Any],
) -> str | None:
    release_state = {
        "release_id": str((release or {}).get("release_id") or "").strip(),
        "release_version": str((release or {}).get("release_version") or "").strip(),
        "fingerprint": str((release or {}).get("fingerprint") or "").strip(),
        "materialization_version": str((release or {}).get("materialization_version") or "").strip(),
    }
    stored_state = {
        "release_id": str(installation_state.get("active_release_id") or "").strip(),
        "release_version": str(installation_state.get("active_release_version") or "").strip(),
        "fingerprint": str(installation_state.get("active_release_fingerprint") or "").strip(),
        "materialization_version": str(installation_state.get("materialization_version") or "").strip(),
    }
    if not any(release_state.values()) and not any(stored_state.values()):
        return None
    if not release_state["fingerprint"]:
        return "active_release_file_missing"
    if not stored_state["fingerprint"]:
        return "installation_state_missing_active_release"
    checks = (
        ("release_id", "active_release_id_mismatch"),
        ("release_version", "active_release_version_mismatch"),
        ("materialization_version", "materialization_version_mismatch"),
        ("fingerprint", "active_release_fingerprint_mismatch"),
    )
    for field_name, reason in checks:
        if stored_state[field_name] and release_state[field_name] != stored_state[field_name]:
            return reason
    return None
