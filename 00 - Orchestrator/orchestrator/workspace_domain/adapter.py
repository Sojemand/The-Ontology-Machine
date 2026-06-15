from __future__ import annotations

from typing import Any, Mapping


def owner_response(
    *,
    owner_action: str,
    capability: str,
    target_identity: Mapping[str, Any],
    output_refs: Mapping[str, Any],
    target_identity_proof: Mapping[str, Any],
    receipt_fields: Mapping[str, Any],
    diagnostics: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    status: str = "ok",
    summary: str = "",
) -> dict[str, Any]:
    detail = {
        "schema_version": "kernel.pipeline_owner_result.v1",
        "owner_module": "00 - Orchestrator",
        "owner_action": owner_action,
        "capability": capability,
        "status": status,
        "target_identity": dict(target_identity),
        "artifact_refs": dict(output_refs),
        "receipt_fields": dict(receipt_fields),
        "diagnostics": list(diagnostics or ()),
        "warnings": list(warnings or ()),
    }
    detail.update(dict(output_refs))
    return {
        "status": "ok",
        "headline": owner_action,
        "summary_lines": [summary] if summary else [],
        "detail": detail,
        "output_refs": dict(output_refs),
        "target_identity_proof": dict(target_identity_proof),
        "receipt_fields": dict(receipt_fields),
        "diagnostics": list(diagnostics or ()),
        "warnings": list(warnings or ()),
    }
