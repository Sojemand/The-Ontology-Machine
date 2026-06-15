from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def path_hash(value: str | Path) -> str:
    return "sha256:" + stable_hash(str(Path(value).expanduser().resolve(strict=False)))


def owner_ok(
    *,
    owner_action: str,
    capability: str,
    target_identity: Mapping[str, Any],
    output_refs: Mapping[str, Any],
    receipt_fields: Mapping[str, Any],
    diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "headline": owner_action,
        "summary_lines": [],
        "detail": {
            "schema_version": "kernel.pipeline_owner_result.v1",
            "owner_module": "05 - Corpus Builder",
            "owner_action": owner_action,
            "capability": capability,
            "status": "ok",
            "target_identity": dict(target_identity),
            "artifact_refs": dict(output_refs),
            "receipt_fields": dict(receipt_fields),
            "diagnostics": list(diagnostics or ()),
            "warnings": [],
            **dict(output_refs),
        },
        "output_refs": dict(output_refs),
        "target_identity_proof": {
            key: value
            for key, value in dict(target_identity).items()
            if key.endswith("_hash") or key in {"merge_run_id", "pipeline_batch_id", "source_database_ids", "target_database_id"}
        },
        "receipt_fields": dict(receipt_fields),
        "diagnostics": list(diagnostics or ()),
    }
