from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.workflows.database_creation.custom_projection_taxonomy_helpers import (
    taxonomy_allowed_codes,
    taxonomy_allowed_codes_by_section,
    taxonomy_fallback_codes,
    taxonomy_fallback_codes_view,
    taxonomy_promotion_slots,
    taxonomy_term_summaries,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import write_json_file


def build_taxonomy_projection_authoring_view(
    taxonomy_ref: Mapping[str, Any],
    *,
    artifact_root: str | Path | None = None,
    analysis_run_id: str | None = None,
    sample_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    allowed_codes = taxonomy_allowed_codes(taxonomy_ref)
    fallback_codes = taxonomy_fallback_codes(taxonomy_ref, allowed_codes)
    view = {
        "schema_version": "kernel.taxonomy_projection_authoring_view.v1",
        "taxonomy_ref": _authoring_taxonomy_ref(taxonomy_ref),
        "budget_policy": {
            "view_mode": "complete",
            "source": "phase9.database_creation",
            "sample_scope_hash": stable_hash(str(sorted((sample_scope or {}).items()))),
        },
        "allowed_codes": taxonomy_allowed_codes_by_section(taxonomy_ref),
        "term_summaries": taxonomy_term_summaries(taxonomy_ref, allowed_codes),
        "promotion_slots": taxonomy_promotion_slots(taxonomy_ref),
        "fallback_codes": taxonomy_fallback_codes_view(taxonomy_ref, fallback_codes),
    }
    if artifact_root is not None and analysis_run_id:
        path = (
            Path(artifact_root)
            / "proj_sa"
            / analysis_run_id
            / "tax_view.json"
        )
        write_json_file(path, view)
    return view


def _authoring_taxonomy_ref(taxonomy_ref: Mapping[str, Any]) -> dict[str, str]:
    return {
        "source": str(taxonomy_ref.get("source") or "active"),
        "taxonomy_id": str(taxonomy_ref.get("taxonomy_id", "")),
        "taxonomy_version": str(taxonomy_ref.get("taxonomy_version") or taxonomy_ref.get("release_version") or "unversioned"),
        "taxonomy_fingerprint": str(taxonomy_ref.get("taxonomy_fingerprint") or taxonomy_ref.get("fingerprint") or ""),
    }
