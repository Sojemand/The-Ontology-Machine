from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool


def normalizer_authoring_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "derive_working_release_from_blueprint",
            "Copy one immutable default blueprint into the workspace-local working source package under artifact_folder/.vp/n. This does not validate, compile, export, activate, or edit the global default line.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "blueprint_ref": {"type": "string", "description": "Checked-in default blueprint id."},
                "target_release_id": {"type": "string", "description": "Optional release id to write into the derived working source package."},
                "target_release_version": {"type": "string", "description": "Optional release version to write into the derived working source package."},
            },
            required=("artifact_folder", "blueprint_ref"),
        ),
        _tool(
            "create_locale_scaffold",
            "Create locale-scoped source files in artifact_folder/.vp/n by copying an existing locale. This does not translate, validate, compile, export, activate, or edit the global default line.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "source_locale": {"type": "string", "description": "Existing locale to copy from."},
                "target_locale": {"type": "string", "description": "New locale for labels/guidance."},
                "overwrite_existing": {"type": "boolean", "default": False},
            },
            required=("artifact_folder", "source_locale", "target_locale"),
        ),
        _tool(
            "create_minimal_custom_release",
            "Replace only the workspace-local working source package with a small custom master taxonomy and one matching projection. This does not inspect samples, validate, compile, export, activate, or edit the global default line.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns this custom release under .vp/n."},
                "language": {"type": "string", "description": "Locale for field labels and extraction guidance."},
                "release_id": {"type": "string", "description": "Optional stable release id. Omit to use semantic_release.<projection_id>."},
                "release_version": {"type": "string", "description": "Optional version label. Omit to keep the current working version."},
                "projection_id": {"type": "string", "description": "Stable machine name for the one custom profile, e.g. fantasy.story.custom.v1."},
                "archive_label": {"type": "string", "description": "Human-readable archive/profile name."},
                "archive_description": {"type": "string", "description": "Plain-language purpose based on the user's documents or inspected sample."},
                "domain": {"type": "object", "description": "Optional {code,label,description,aliases} for the custom domain."},
                "category": {"type": "object", "description": "Optional {code,label,description,aliases} for the custom category."},
                "subcategory": {"type": "object", "description": "Optional {code,label,description,aliases} for the custom subcategory."},
                "document_types": {"type": "array", "items": {"type": "object"}, "description": "Custom document types. Each item needs code, label, description; aliases optional."},
                "field_codes": {"type": "array", "items": {"type": "object"}, "description": "Custom fields. Each item needs code, label, description; aliases/value_type optional."},
                "row_types": {"type": "array", "items": {"type": "object"}, "description": "Optional custom repeated row types."},
                "cell_codes": {"type": "array", "items": {"type": "object"}, "description": "Optional custom row cell codes."},
                "text_markers": {"type": "array", "items": {"type": "string"}, "description": "Routing words that should identify this archive."},
                "when_to_use": {"type": "string"},
                "avoid_when": {"type": "string"},
            },
            required=("artifact_folder", "language", "projection_id", "archive_label", "archive_description", "document_types", "field_codes"),
        ),
        _tool(
            "create_projection_draft",
            "Create one workspace-local projection draft using only master terms already present in the working source package. This cannot create master terms and does not validate, compile, export, activate, or edit the global default line.",
            _projection_properties(),
            required=(
                "artifact_folder",
                "projection_id",
                "template_projection_id",
                "language",
                "label",
                "description",
                "when_to_use",
                "avoid_when",
                "example_document_types",
                "domain_ids",
                "include_document_types",
                "include_categories",
                "include_subcategories",
                "include_field_codes",
                "include_row_types",
                "include_cell_codes",
            ),
        ),
        _tool(
            "generate_locale_translation_payload",
            "Generate a reviewable translation payload from a working source package without writing files. This does not scaffold, translate/apply, validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Optional workspace root for reading the working source package under .vp/n."},
                "source_language": {"type": "string", "description": "Existing locale to translate from."},
                "target_language": {"type": "string", "description": "Locale to generate."},
                "model": {"type": "string"},
                "max_output_tokens": {"type": "integer", "minimum": 1},
            },
            required=("source_language", "target_language", "model", "max_output_tokens"),
        ),
        _tool(
            "translate_working_release_locale",
            "Apply an explicit translation_payload to one scaffolded workspace-local locale. This does not generate payloads, validate, compile, export, activate, or edit the global default line.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "source_locale": {"type": "string", "description": "Existing source locale."},
                "target_locale": {"type": "string", "description": "Existing scaffolded target locale to update."},
                "translation_payload": {"type": "object", "additionalProperties": True},
                "overwrite_existing": {"type": "boolean", "default": False},
            },
            required=("artifact_folder", "source_locale", "target_locale", "translation_payload"),
        ),
    ]


def _projection_properties() -> dict[str, Any]:
    return {
        "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
        "projection_id": {"type": "string", "description": "Stable machine name such as fantasy.story.default.v1."},
        "template_projection_id": {"type": "string", "description": "Existing profile to copy as a starting point."},
        "language": {"type": "string", "description": "Locale for this profile's labels and guidance."},
        "label": {"type": "string", "description": "Human-readable profile name."},
        "description": {"type": "string", "description": "What this profile is for in plain language."},
        "when_to_use": {"type": "string", "description": "Guidance for documents that should use this profile."},
        "avoid_when": {"type": "string", "description": "Guidance for documents that should not use this profile."},
        "example_document_types": {"type": "string", "description": "Newline/comma separated examples."},
        "text_markers": {"type": "string", "description": "Newline/comma separated routing words or phrases."},
        "primary_domain": {"type": "string", "description": "Optional existing domain id to route this profile under."},
        "domain_ids": {"type": "string", "description": "Existing domain ids."},
        "include_document_types": {"type": "string", "description": "Existing document type codes to allow."},
        "include_categories": {"type": "string", "description": "Existing category codes to allow."},
        "include_subcategories": {"type": "string", "description": "Existing subcategory codes to allow."},
        "include_field_codes": {"type": "string", "description": "Existing field codes to allow."},
        "include_row_types": {"type": "string", "description": "Existing row type codes to allow."},
        "include_cell_codes": {"type": "string", "description": "Existing cell codes to allow."},
        "overwrite_existing": {"type": "boolean", "default": False},
    }


__all__ = ["normalizer_authoring_tools"]
