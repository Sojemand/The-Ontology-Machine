from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.blockers import make_state_blocker
from semantic_control_kernel.domain.state_machine.models import TargetIdentity
from semantic_control_kernel.repository.paths import stable_hash


def blocker_payload(
    code: str,
    target_identity: TargetIdentity,
    required_state: str,
    actual_state: str,
    evidence_refs: tuple[str, ...],
) -> dict[str, Any]:
    return make_state_blocker(
        blocker_code=code,
        function_or_route="KernelStateResolver",
        required_state=required_state,
        actual_state=actual_state,
        target_identity=target_identity.to_dict(),
        state_snapshot_id="pending",
        evidence_refs=evidence_refs,
    ).to_dict()


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def owner_evidence_matches(payload: Mapping[str, Any], target_identity: TargetIdentity) -> bool:
    target = payload.get("target_identity")
    if not isinstance(target, Mapping):
        return True
    for key in ("target_hash", "database_path_hash"):
        if target.get(key) and target.get(key) != target_identity.to_dict().get(key):
            return False
    return True


def record_count(payload: Mapping[str, Any]) -> int | None:
    for key in ("materialized_record_count", "record_count", "records"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    record_counts = payload.get("record_counts")
    if isinstance(record_counts, Mapping):
        for key in ("projected_records", "normalized_records", "documents"):
            value = record_counts.get(key)
            if isinstance(value, int):
                return value
    return None


def materialization_count(payload: Mapping[str, Any]) -> int:
    refs = payload.get("materialization_refs") or payload.get("refs")
    if isinstance(refs, list):
        return len(refs)
    count = payload.get("record_count")
    return int(count) if isinstance(count, int) else 0


def release_complete(payload: Mapping[str, Any]) -> bool:
    has_taxonomy = bool(payload.get("taxonomy_fingerprint") or payload.get("taxonomy_id") or payload.get("has_taxonomy"))
    projection_count = payload.get("projection_count")
    has_projection = bool(payload.get("projection_set_hash") or payload.get("projection_fingerprints"))
    if isinstance(projection_count, int):
        has_projection = projection_count > 0
    if payload.get("complete") is False or payload.get("is_complete") is False:
        return False
    return has_taxonomy and has_projection and bool(payload.get("release_fingerprint"))


def has_blocker(blocking: list[dict[str, Any]], *codes: str) -> bool:
    code_set = set(codes)
    return any(item.get("blocker_code") in code_set for item in blocking)


def state_snapshot_id(
    target_identity: TargetIdentity,
    database_emptiness: str,
    semantic_state: str,
    blocking: list[dict[str, Any]],
    active_lock_refs: list[dict[str, Any]],
    evidence_ids: tuple[str, ...],
    now_utc: datetime,
) -> str:
    basis = {
        "active_lock_refs": active_lock_refs,
        "blocking": [{k: v for k, v in item.items() if k != "state_snapshot_id"} for item in blocking],
        "database_emptiness": database_emptiness,
        "evidence_ids": evidence_ids,
        "now_utc": now_utc.isoformat(),
        "semantic_state": semantic_state,
        "target_identity": target_identity.to_dict(),
    }
    return f"state_{stable_hash(json.dumps(basis, sort_keys=True, separators=(',', ':')))}"
