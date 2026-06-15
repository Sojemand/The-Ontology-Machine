from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import owner_ok
from .cleanup_journal import write_cleanup_journal
from .cleanup_mutation import mutate_cleanup_scope
from .cleanup_workflow_paths import (
    JOURNAL_SCHEMA_VERSION,
    _cleanup_journal_path,
    _cleanup_plan_path,
    _mapping,
    _resolve_database_path,
    _validate_target_identity,
)
from .cleanup_workflow_plan import (
    PLAN_SCHEMA_VERSION,
    _load_cleanup_plan,
    _load_confirmation,
    _validate_confirmation,
    _validate_plan_against_source,
)
from .cleanup_workflow_source import _load_source_manifest, _preserved_original_refs, _removed_artifact_refs
from .path_io import write_json


def cleanup_pipeline_batch_materialization(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_root_text = str(payload.get("artifact_root") or "").strip()
    if not artifact_root_text:
        raise ValueError("artifact_root is required.")
    artifact_root = Path(artifact_root_text).resolve(strict=False)
    target_identity = _mapping(payload, "target_identity")
    _validate_target_identity(artifact_root, target_identity)
    plan = _load_cleanup_plan(payload, artifact_root)
    confirmation = _load_confirmation(payload, artifact_root)
    _validate_confirmation(confirmation, target_identity, plan)
    source_manifest, source_ref = _load_source_manifest(plan, artifact_root)
    _validate_plan_against_source(plan, source_manifest)

    cleanup_plan_path = _cleanup_plan_path(artifact_root, str(plan["cleanup_plan_id"]))
    write_json(cleanup_plan_path, plan)

    removed_artifact_refs = _removed_artifact_refs(plan, source_manifest, artifact_root)
    preserved_original_refs = _preserved_original_refs(source_manifest)
    mutation_report = mutate_cleanup_scope(
        database_path=_resolve_database_path(payload, plan, source_manifest, artifact_root),
        artifact_root=artifact_root,
        record_refs=[dict(item) for item in plan["affected_records"] if isinstance(item, Mapping)],
        artifact_refs=removed_artifact_refs,
    )
    journal_path = _cleanup_journal_path(artifact_root, plan)
    journal = {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "cleanup_plan_ref": {"artifact_path": cleanup_plan_path.relative_to(artifact_root).as_posix()},
        "cleanup_scope": plan["cleanup_scope"],
        "removed_record_refs": list(plan["affected_records"]),
        "removed_artifact_refs": mutation_report["removed_artifact_refs"],
        "preserved_original_refs": preserved_original_refs,
        "post_cleanup_counts": mutation_report["post_cleanup_counts"],
        "journal_entries": [
            {
                "status": "mutated",
                "source_manifest_ref": source_ref,
                "removed_record_count": mutation_report["removed_database_record_count"],
                "removed_artifact_count": mutation_report["removed_artifact_count"],
            }
        ],
    }
    write_cleanup_journal(journal_path, journal)

    output = {
        "cleanup_journal_ref": {"artifact_path": journal_path.relative_to(artifact_root).as_posix()},
        "removed_record_refs": list(plan["affected_records"]),
        "removed_artifact_refs": mutation_report["removed_artifact_refs"],
        "preserved_original_refs": preserved_original_refs,
        "post_cleanup_counts": journal["post_cleanup_counts"],
        "journal_entries": journal["journal_entries"],
        "final_status": "completed",
        "partial_failure_ref": {},
    }
    return owner_ok(
        owner_action="cleanup_pipeline_batch_materialization",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=target_identity,
        output_refs=output,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "cleanup_pipeline_batch_materialization",
            "pipeline_batch_id": str(plan.get("source_manifest_ref", {}).get("pipeline_batch_id") or ""),
        },
    )
