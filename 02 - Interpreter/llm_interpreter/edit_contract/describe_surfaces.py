"""Descriptor builders for Interpreter edit surfaces."""
from __future__ import annotations

from .env_repository import EXECUTION_LIMIT_FIELD_GROUPS, RUNTIME_POLICY_FIELD_GROUPS, field_groups
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    EXECUTION_LIMITS_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    RUNTIME_POLICY_ENV_SURFACE_ID,
)


def describe_surfaces() -> list[dict]:
    return [
        _descriptor(
            RUNTIME_POLICY_ENV_SURFACE_ID,
            label="Runtime Policy",
            kind="settings",
            storage_kind="env_file",
            source_path="config/.env",
            editable=True,
            preview=["form", "json", "diff"],
            runtime_impact="next_run",
            drift_status="split_owner",
            section="Settings",
            field_groups=field_groups(RUNTIME_POLICY_FIELD_GROUPS),
        ),
        _descriptor(
            EXECUTION_LIMITS_SURFACE_ID,
            label="Execution Limits",
            kind="settings",
            storage_kind="env_file",
            source_path="config/.env",
            editable=True,
            preview=["form", "json", "diff"],
            runtime_impact="next_run",
            drift_status="split_owner",
            section="Settings",
            field_groups=field_groups(EXECUTION_LIMIT_FIELD_GROUPS),
        ),
        _descriptor(
            PROMPT_BUNDLE_SURFACE_ID,
            label="Prompt Bundle",
            kind="prompt_bundle",
            storage_kind="compound_asset",
            source_path="config/prompt_bundle",
            editable=True,
            preview=["json", "diff"],
            runtime_impact="next_run",
            drift_status="implicit_code_default",
            section="Prompts/Assets",
        ),
        _descriptor(
            OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
            label="Output Contract Preview",
            kind="inspection",
            storage_kind="derived_readonly",
            source_path="llm_interpreter/prompts/schema.py",
            editable=False,
            preview=["summary", "json"],
            runtime_impact="read_only_reference",
            drift_status="implicit_code_default",
            section="Preview/Drift",
        ),
        _descriptor(
            DEBUG_CAPABILITIES_SURFACE_ID,
            label="Debug Capabilities",
            kind="capability_summary",
            storage_kind="derived_readonly",
            source_path="module-manifest.json",
            editable=False,
            preview=["summary", "json"],
            runtime_impact="read_only_reference",
            drift_status="explicit_file",
            section="Operations",
        ),
    ]


def _descriptor(
    surface_id: str,
    *,
    label: str,
    kind: str,
    storage_kind: str,
    source_path: str,
    editable: bool,
    preview: list[str],
    runtime_impact: str,
    drift_status: str,
    section: str,
    field_groups: list[dict[str, object]] | None = None,
) -> dict:
    descriptor = {
        "module_key": "interpreter",
        "surface_id": surface_id,
        "label": label,
        "kind": kind,
        "owner": "interpreter",
        "storage_kind": storage_kind,
        "source_path": source_path,
        "editable": editable,
        "validation": {"mode": "owner_contract", "fail_closed": editable},
        "preview": list(preview),
        "operation_links": [],
        "runtime_impact": runtime_impact,
        "drift_status": drift_status,
        "section": section,
    }
    if field_groups:
        descriptor["field_groups"] = field_groups
    return descriptor
