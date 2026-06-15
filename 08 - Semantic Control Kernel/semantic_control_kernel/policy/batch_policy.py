from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash


PIPELINE_BATCH_ID_RE = re.compile(r"^pbt_\d{14}_[0-9a-f]{8}_\d+$")
PIPELINE_BATCH_KINDS = (
    "manual_ingest",
    "sample_ingest",
    "reingest_all_originals",
    "reingest_selected_samples",
    "workflow_continuation_ingest",
)
FINAL_BATCH_STATUS = "finalized"


def allocate_pipeline_batch_id(
    workflow_run_id: str,
    *,
    attempt_index: int = 1,
    now: datetime | None = None,
) -> str:
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
    workflow_hash = hashlib.sha256(workflow_run_id.encode("utf-8")).hexdigest()[:8]
    return f"pbt_{timestamp}_{workflow_hash}_{attempt_index}"


def is_valid_pipeline_batch_id(value: str) -> bool:
    return bool(PIPELINE_BATCH_ID_RE.match(value))


def canonical_manifest_fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = deepcopy(dict(payload))
    canonical["manifest_fingerprint"] = ""
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def with_manifest_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    manifest = deepcopy(dict(payload))
    manifest["manifest_fingerprint"] = canonical_manifest_fingerprint(manifest)
    return manifest


def pipeline_batch_manifest_path(artifact_root_path: str | Path, pipeline_batch_id: str) -> Path:
    return Path(artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "pipeline_batch_manifest.json"


def pending_batch_manifest_path(artifact_root_path: str | Path, pipeline_batch_id: str) -> Path:
    return Path(artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "pending_pipeline_batch_manifest.json"


def batch_run_journal_path(artifact_root_path: str | Path, pipeline_batch_id: str) -> Path:
    return Path(artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "batch_run_journal.jsonl"


def correlation_report_path(artifact_root_path: str | Path, pipeline_batch_id: str) -> Path:
    return Path(artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "correlation_report.json"


def sample_selection_manifest_path(artifact_root_path: str | Path, sample_selection_id: str) -> Path:
    return (
        Path(artifact_root_path)
        / "Documents"
        / "logs"
        / "pipeline_batches"
        / "selections"
        / sample_selection_id
        / "sample_selection_manifest.json"
    )


def relative_artifact_ref_is_safe(ref: str, artifact_root_path: str | Path) -> bool:
    if not ref:
        return True
    candidate = Path(ref)
    if candidate.is_absolute():
        try:
            candidate.resolve(strict=False).relative_to(Path(artifact_root_path).resolve(strict=False))
            return True
        except ValueError:
            return False
    return ".." not in candidate.parts


def build_materialization_ref(
    *,
    pipeline_batch_id: str,
    document_id: str,
    record_id: str,
    semantic_release_id: str,
    semantic_release_version: str,
    release_fingerprint: str,
    taxonomy_fingerprint: str,
    projection_id: str,
    projection_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema_version": "kernel.record_semantic_materialization_ref.v1",
        "pipeline_batch_id": pipeline_batch_id,
        "document_id": document_id,
        "record_id": record_id,
        "semantic_release_id": semantic_release_id,
        "semantic_release_version": semantic_release_version,
        "release_fingerprint": release_fingerprint,
        "taxonomy_fingerprint": taxonomy_fingerprint,
        "projection_id": projection_id,
        "projection_fingerprint": projection_fingerprint,
    }


def record_counts_from_materialized_records(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    documents = {str(record.get("document_id", "")) for record in records if record.get("document_id")}
    return {
        "documents": len(documents),
        "normalized_records": len(records),
        "projected_records": len(records),
        "embeddings": sum(1 for record in records if record.get("embedding_ref")),
        "error_cases": 0,
    }


def sample_selection_id(workflow_run_id: str, seed: str) -> str:
    return "sel_" + stable_hash(f"{workflow_run_id}:{seed}")[:20]


def cleanup_plan_id(workflow_run_id: str, seed: str) -> str:
    return "cln_" + stable_hash(f"{workflow_run_id}:{seed}")[:20]


def journal_id(workflow_run_id: str, seed: str) -> str:
    return "jrnl_" + stable_hash(f"{workflow_run_id}:{seed}")[:20]


def reset_manifest_id(workflow_run_id: str, seed: str) -> str:
    return "rstman_" + stable_hash(f"{workflow_run_id}:{seed}")[:18]


def artifact_ref(path: Path, root: Path) -> dict[str, str]:
    try:
        return {"artifact_path": path.relative_to(root).as_posix()}
    except ValueError:
        return {"artifact_path": str(path)}
