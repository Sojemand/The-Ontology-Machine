from __future__ import annotations

import json
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash


PHASE19_OWNER_REQUEST_SCHEMA_VERSION = "kernel.pipeline_owner_request.v1"


def phase19_request_fingerprint(payload: Mapping[str, Any]) -> str:
    fingerprint_seed = dict(payload)
    fingerprint_seed["request_fingerprint"] = ""
    canonical = json.dumps(
        fingerprint_seed,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return stable_hash(canonical)
