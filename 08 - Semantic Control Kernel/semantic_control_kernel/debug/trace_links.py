from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.paths import utc_iso


def build_trace_link(
    *,
    trace_id: str,
    workflow_run_id: str,
    object_kind: str,
    object_id: str,
    object_ref: Mapping[str, Any] | str,
) -> dict[str, Any]:
    return {
        "schema_version": "debug.trace_link.v1",
        "trace_id": trace_id,
        "workflow_run_id": workflow_run_id,
        "object_kind": object_kind,
        "object_id": object_id,
        "object_ref": dict(object_ref) if isinstance(object_ref, Mapping) else str(object_ref),
        "created_at": utc_iso(),
    }
