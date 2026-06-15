from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.phase19_requests import (
    PHASE19_OWNER_REQUEST_SCHEMA_VERSION,
    phase19_request_fingerprint,
)
from semantic_control_kernel.repository.paths import utc_iso


class AdapterIdentityMixin:
    def target_identity(
        self,
        payload: Mapping[str, Any] | None,
        *,
        database_path: str | Path | None = None,
        artifact_root_path: str | Path | None = None,
        pipeline_batch_id: str | None = None,
        merge_run_id: str | None = None,
        release_ref: Mapping[str, Any] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(payload or {})
        target_identity = source.get("target_identity")
        identity = dict(target_identity) if isinstance(target_identity, Mapping) else {}
        for key in ("database_path_hash", "artifact_root_path_hash", "release_id", "release_version", "release_fingerprint"):
            value = source.get(key)
            if value and key not in identity:
                identity[key] = str(value)
        if database_path and "database_path_hash" not in identity:
            identity["database_path_hash"] = self.owner_path_hash(database_path)
        if artifact_root_path and "artifact_root_path_hash" not in identity:
            identity["artifact_root_path_hash"] = self.owner_path_hash(artifact_root_path)
        if pipeline_batch_id and "pipeline_batch_id" not in identity:
            identity["pipeline_batch_id"] = pipeline_batch_id
        if merge_run_id and "merge_run_id" not in identity:
            identity["merge_run_id"] = merge_run_id
        if isinstance(release_ref, Mapping):
            for key in ("release_id", "release_version", "release_fingerprint"):
                value = release_ref.get(key)
                if value and key not in identity:
                    identity[key] = str(value)
        if isinstance(extra, Mapping):
            for key, value in extra.items():
                if value and key not in identity:
                    identity[key] = value
        return {
            key: value
            for key, value in identity.items()
            if value not in ("", None, [], {})
        }

    def phase19_request(
        self,
        *,
        owner_action: str,
        request_payload: Mapping[str, Any] | None,
        target_identity: Mapping[str, Any] | None = None,
        **action_fields: Any,
    ) -> dict[str, Any]:
        payload = dict(request_payload or {})
        resolved_target_identity = dict(target_identity or payload.get("target_identity") or {})
        owner_request = {
            "schema_version": PHASE19_OWNER_REQUEST_SCHEMA_VERSION,
            "owner_action": owner_action,
            "workflow_run_id": str(payload.get("workflow_run_id") or "wr_phase19"),
            "requested_at": utc_iso(),
            "target_identity": resolved_target_identity,
            **action_fields,
        }
        owner_request["request_fingerprint"] = phase19_request_fingerprint(owner_request)
        return owner_request
