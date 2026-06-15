from __future__ import annotations

from typing import Any, Mapping


def build_cleanup_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cleanup_scope": str(payload.get("cleanup_scope") or "selected_batch"),
        "affected_records": list(payload.get("affected_records", [])),
        "affected_artifacts": list(payload.get("affected_artifacts", [])),
        "affected_embeddings": list(payload.get("affected_embeddings", [])),
        "original_refs_preserved": list(payload.get("original_refs_preserved", [])),
    }
