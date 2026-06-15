from __future__ import annotations

from .tool_handler_deps import *


def derive_working_release_from_blueprint(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    payload = {
        "action": "derive_working_release_from_blueprint",
        "blueprint_ref": _required_text(arguments, "blueprint_ref"),
    }
    _add_optional(payload, arguments, "target_release_id")
    _add_optional(payload, arguments, "target_release_version")
    return _workspace_authoring_result(artifact_path, payload)


def create_minimal_custom_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    projection_id = _required_text(arguments, "projection_id")
    payload: dict[str, Any] = {
        "action": "create_minimal_custom_release",
        "language": _required_text(arguments, "language"),
        "release_id": _optional_text(arguments, "release_id") or f"semantic_release.{projection_id}",
        "projection_id": projection_id,
        "archive_label": _required_text(arguments, "archive_label"),
        "archive_description": _required_text(arguments, "archive_description"),
        "document_types": _required_list(arguments, "document_types"),
        "field_codes": _required_list(arguments, "field_codes"),
    }
    for key in (
        "release_version",
        "domain",
        "category",
        "subcategory",
        "row_types",
        "cell_codes",
        "text_markers",
        "when_to_use",
        "avoid_when",
    ):
        if key in arguments and arguments[key] not in (None, ""):
            payload[key] = arguments[key]
    return _workspace_authoring_result(artifact_path, payload)


def create_projection_draft(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    payload = {
        "action": "create_projection_draft",
        "projection_id": _required_text(arguments, "projection_id"),
        "template_projection_id": _required_text(arguments, "template_projection_id"),
        "locale": _required_text(arguments, "language"),
        "label": _required_text(arguments, "label"),
        "description": _required_text(arguments, "description"),
        "when_to_use": _required_text(arguments, "when_to_use"),
        "avoid_when": _required_text(arguments, "avoid_when"),
        "example_document_types": _required_text(arguments, "example_document_types"),
        "domain_ids": _required_text(arguments, "domain_ids"),
        "include_document_types": _required_text(arguments, "include_document_types"),
        "include_categories": _required_text(arguments, "include_categories"),
        "include_subcategories": _required_text(arguments, "include_subcategories"),
        "include_field_codes": _required_text(arguments, "include_field_codes"),
        "include_row_types": _required_text(arguments, "include_row_types"),
        "include_cell_codes": _required_text(arguments, "include_cell_codes"),
    }
    for key in (
        "text_markers",
        "primary_domain",
    ):
        _add_optional(payload, arguments, key)
    if "overwrite_existing" in arguments:
        payload["overwrite_existing"] = _optional_bool(arguments, "overwrite_existing", default=False)
    return _workspace_authoring_result(artifact_path, payload)


def generate_locale_translation_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "action": "generate_locale_translation_payload",
        "source_locale": _required_text(arguments, "source_language"),
        "target_locale": _required_text(arguments, "target_language"),
        "model": _required_text(arguments, "model"),
        "max_output_tokens": _positive_int(arguments.get("max_output_tokens"), "max_output_tokens"),
    }
    artifact_folder = _optional_text(arguments, "artifact_folder")
    if artifact_folder:
        return _workspace_authoring_result(Path(artifact_folder).expanduser().resolve(), payload)
    return _invoke_edit("normalizer", payload)


def translate_working_release_locale(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    payload = {
        "action": "translate_release_locale",
        "source_locale": _required_text(arguments, "source_locale"),
        "target_locale": _required_text(arguments, "target_locale"),
        "translation_payload": _required_mapping(arguments, "translation_payload"),
    }
    if "overwrite_existing" in arguments:
        payload["overwrite_existing"] = _optional_bool(arguments, "overwrite_existing", default=False)
    return _workspace_authoring_result(artifact_path, payload)


def _workspace_authoring_result(artifact_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    result = _invoke_workspace_normalizer_edit(artifact_path, payload)
    return {
        **result,
        "artifact_folder": str(artifact_path),
        "normalizer_authoring_home": str(_workspace_normalizer_home(artifact_path)),
        "authoring_scope": "workspace",
    }

__all__ = [name for name in globals() if not name.startswith("__")]
