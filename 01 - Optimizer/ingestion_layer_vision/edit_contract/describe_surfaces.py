"""Descriptor builders for Optimizer edit surfaces."""
from __future__ import annotations

from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    OCR_PROMPT_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    SETTINGS_FIELD_GROUPS,
    SETTINGS_SURFACE_ID,
    field_groups,
)


def describe_surfaces() -> list[dict]:
    return [
        _descriptor(
            SETTINGS_SURFACE_ID,
            label="Settings",
            kind="settings",
            storage_kind="yaml_file",
            source_path="config/config.yaml",
            editable=True,
            preview=["form", "yaml", "diff"],
            runtime_impact="next_run",
            drift_status="explicit_file",
            section="Settings",
            field_groups=field_groups(SETTINGS_FIELD_GROUPS),
        ),
        _descriptor(
            OCR_PROMPT_SURFACE_ID,
            label="LLM-OCR Prompt",
            kind="prompt_bundle",
            storage_kind="text_file",
            source_path="config/optimizer_ocr_prompt.md",
            editable=True,
            preview=["prompt", "diff"],
            runtime_impact="next_run",
            drift_status="explicit_file",
            section="Prompts/Assets",
        ),
        _descriptor(
            OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
            label="Output Contract Preview",
            kind="inspection",
            storage_kind="derived_readonly",
            source_path="ingestion_layer_vision/models/raw_workflow.py",
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
        "module_key": "optimizer",
        "surface_id": surface_id,
        "label": label,
        "kind": kind,
        "owner": "optimizer",
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
