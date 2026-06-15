"""Descriptor builders for validator edit surfaces."""
from __future__ import annotations

from .types import DEBUG_CAPABILITIES_SURFACE_ID, REPORT_POLICY_SURFACE_ID, SETTINGS_SURFACE_ID
from .validation import POLICY_FIELDS, SETTINGS_FIELDS


def describe_surfaces() -> list[dict]:
    return [
        _descriptor(
            SETTINGS_SURFACE_ID,
            label="Settings",
            kind="settings",
            editable=True,
            source_path="config/config.json",
            preview=["form", "json", "summary", "diff"],
            section="Settings",
            field_groups=[
                {"label": "Checks", "fields": [field for field in SETTINGS_FIELDS if field.startswith("checks.")]},
                {"label": "Match", "fields": [field for field in SETTINGS_FIELDS if field.startswith("match.")]},
            ],
        ),
        _descriptor(
            REPORT_POLICY_SURFACE_ID,
            label="Report Preview Policy",
            kind="policy",
            editable=True,
            source_path="config/config.json",
            preview=["form", "json", "summary", "diff"],
            section="Settings",
            field_groups=[{"label": "Report Preview Policy", "fields": list(POLICY_FIELDS)}],
        ),
        _descriptor(
            DEBUG_CAPABILITIES_SURFACE_ID,
            label="Debug Capabilities",
            kind="capability_summary",
            editable=False,
            source_path="module-manifest.json",
            preview=["summary", "json", "table"],
            section="Operations",
        ),
    ]


def _descriptor(
    surface_id: str,
    *,
    label: str,
    kind: str,
    editable: bool,
    source_path: str,
    preview: list[str],
    section: str,
    field_groups: list[dict[str, object]] | None = None,
) -> dict:
    descriptor = {
        "module_key": "validator",
        "surface_id": surface_id,
        "label": label,
        "kind": kind,
        "owner": "validator",
        "storage_kind": "derived_readonly" if not editable else "json_file",
        "source_path": source_path,
        "editable": editable,
        "validation": {"mode": "owner_contract", "fail_closed": editable},
        "preview": list(preview),
        "operation_links": [],
        "runtime_impact": "read_only_reference" if not editable else "next_run",
        "drift_status": "explicit_file",
        "section": section,
    }
    if field_groups:
        descriptor["field_groups"] = field_groups
    return descriptor
