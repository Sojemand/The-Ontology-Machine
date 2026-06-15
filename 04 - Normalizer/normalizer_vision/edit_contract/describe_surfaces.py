"""Descriptor builders for Normalizer edit surfaces."""
from __future__ import annotations

from . import validation
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    PROMPT_OVERRIDES_SURFACE_ID,
    SETTINGS_SURFACE_ID,
    TAXONOMY_RELEASE_DRAFT_SURFACE_ID,
)


def describe_surfaces(module_root) -> list[dict]:
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
            field_groups=validation.field_groups(),
        ),
        _descriptor(
            PROMPT_OVERRIDES_SURFACE_ID,
            label="Prompt Overrides",
            kind="prompt_bundle",
            storage_kind="json_file",
            source_path="config/prompt_overrides.json",
            editable=True,
            preview=["json", "diff"],
            runtime_impact="next_run",
            drift_status="explicit_file",
            section="Prompts/Assets",
        ),
        _descriptor(
            PROMPT_BUNDLE_SURFACE_ID,
            label="Prompt Bundle",
            kind="prompt_bundle",
            storage_kind="json_file",
            source_path="config/prompt_bundle.json",
            editable=True,
            preview=["json", "diff"],
            runtime_impact="next_run",
            drift_status="explicit_file",
            section="Prompts/Assets",
        ),
        _descriptor(
            TAXONOMY_RELEASE_DRAFT_SURFACE_ID,
            label="Taxonomy / Projection Release",
            kind="taxonomy_release_draft",
            storage_kind="semantic_release_copy",
            source_path="Artifact Tree / Semantic Release/releases/*/release.json",
            editable=True,
            preview=["summary", "diff"],
            runtime_impact="verify_then_apply",
            drift_status="working_copy",
            section="Prompts/Assets",
            editor_kind="taxonomy_release_draft",
            editor_metadata={
                "schema_version": "taxonomy_release_draft.v1",
                "artifact_selection": "open_folder",
                "release_search": "recursive_release_json",
                "copy_policy": "never_mutate_origin",
                "taxonomy_sections": [
                    "domains",
                    "document_types",
                    "categories",
                    "subcategories",
                    "field_codes",
                    "row_types",
                    "cell_codes",
                    "entity_types",
                    "role_types",
                    "relation_types",
                    "promotion_slots",
                ],
                "projection_sections": [
                    "basics",
                    "coverage",
                    "routing",
                    "promotion_rules",
                ],
                "tool_catalog": [
                    "select_artifact_tree",
                    "find_semantic_releases",
                    "load_release_copy",
                    "edit_taxonomy_terms",
                    "edit_projections",
                    "verify_release",
                    "classify_db_update",
                ],
            },
            validate_label="Verify",
            save_label="Write Copy",
        ),
        _descriptor(
            DEBUG_CAPABILITIES_SURFACE_ID,
            label="Debug Capabilities",
            kind="capability_summary",
            storage_kind="derived_readonly",
            source_path="module-manifest.json",
            editable=False,
            preview=["summary", "json", "table"],
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
    operation_links: list[dict[str, object]] | None = None,
    editor_kind: str | None = None,
    editor_metadata: dict[str, object] | None = None,
    action_buttons: list[dict[str, object]] | None = None,
    validate_label: str | None = None,
    save_label: str | None = None,
) -> dict:
    descriptor = {
        "module_key": "normalizer",
        "surface_id": surface_id,
        "label": label,
        "kind": kind,
        "owner": "normalizer",
        "storage_kind": storage_kind,
        "source_path": source_path,
        "editable": editable,
        "validation": {"mode": "owner_contract", "fail_closed": editable},
        "preview": list(preview),
        "operation_links": list(operation_links or []),
        "runtime_impact": runtime_impact,
        "drift_status": drift_status,
        "section": section,
    }
    if editor_kind:
        descriptor["editor_kind"] = editor_kind
    if editor_metadata:
        descriptor["editor_metadata"] = editor_metadata
    if action_buttons:
        descriptor["action_buttons"] = list(action_buttons)
    if field_groups:
        descriptor["field_groups"] = field_groups
    if validate_label:
        descriptor["validate_label"] = validate_label
    if save_label:
        descriptor["save_label"] = save_label
    return descriptor
