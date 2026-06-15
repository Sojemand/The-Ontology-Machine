from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.paths import utc_iso


SUPPORT_REF_KEYS = (
    "schema_version",
    "support_bundle_id",
    "support_bundle_path",
    "created_at",
    "category",
    "workflow_run_id",
    "recovery_event_id",
    "safe_summary",
    "included_refs",
    "redaction_profile",
)


def append_index(path: Path, json_store: AtomicJsonStore, support_ref: Mapping[str, Any]) -> None:
    if path.exists():
        index = json_store.read_json(path)
        refs = [ref for ref in index.get("support_bundle_refs", []) if ref.get("support_bundle_id") != support_ref["support_bundle_id"]]
    else:
        refs = []
    refs.append(dict(support_ref))
    json_store.write_json(path, {"schema_version": "repository.support_bundle_index.v1", "support_bundle_refs": refs, "updated_at": utc_iso()})


def remove_from_index(path: Path, json_store: AtomicJsonStore, support_bundle_id: str) -> None:
    if not path.exists():
        return
    index = json_store.read_json(path)
    refs = [ref for ref in index.get("support_bundle_refs", []) if ref.get("support_bundle_id") != support_bundle_id]
    json_store.write_json(path, {"schema_version": "repository.support_bundle_index.v1", "support_bundle_refs": refs, "updated_at": utc_iso()})


def default_severity(category: str) -> str:
    if category in {"support_only_unrecoverable", "final_llm_validation_failure", "final_error"}:
        return "final_error"
    return "recoverable_error"


def default_retention_class(category: str) -> str:
    if category == "final_llm_validation_failure":
        return "llm_validation_manual"
    if category in {"support_only_unrecoverable", "final_error"}:
        return "final_error_manual"
    return "support_only_manual"


def safe_summary_markdown(manifest: Mapping[str, Any]) -> str:
    lines = [
        "# Support Bundle",
        "",
        f"- Support bundle ID: {manifest['support_bundle_id']}",
        f"- Category: {manifest['category']}",
        f"- Severity: {manifest['severity']}",
        f"- Workflow run ID: {manifest['workflow_run_id']}",
        f"- Workflow tool: {manifest['workflow_tool']}",
        "",
        manifest["safe_summary"],
        "",
    ]
    return "\n".join(lines)
