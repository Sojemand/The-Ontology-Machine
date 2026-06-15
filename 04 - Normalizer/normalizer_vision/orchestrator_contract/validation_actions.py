"""Action and command parsers for the normalizer subprocess contract."""
from __future__ import annotations

from . import value_parsing
from .types import (
    BUILD_PROJECTION_CATALOG_ACTION,
    BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION,
    CREATE_ZERO_SHOT_WORKING_RELEASE_ACTION,
    DEBUG_RUN_ACTION,
    EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION,
    HEALTHCHECK_ACTION,
    LIST_DEFAULT_BLUEPRINTS_ACTION,
    NORMALIZE_DOCUMENT_ACTION,
    PUBLISH_SEMANTIC_RELEASE_ACTION,
    ActionName,
    BuildRuntimeSemanticAssetsCommand,
    CreateZeroShotWorkingReleaseCommand,
    ExportDefaultBlueprintReleaseCommand,
    HealthcheckCommand,
    NormalizeDocumentCommand,
    PublishSemanticReleaseCommand,
)
from .validation_keys import (
    BUILD_PROJECTION_CATALOG_KEYS,
    BUILD_RUNTIME_SEMANTIC_ASSETS_KEYS,
    CREATE_ZERO_SHOT_WORKING_RELEASE_KEYS,
    EXPORT_DEFAULT_BLUEPRINT_RELEASE_KEYS,
    HEALTHCHECK_KEYS,
    LIST_DEFAULT_BLUEPRINTS_KEYS,
    NORMALIZE_DOCUMENT_KEYS,
    PUBLISH_SEMANTIC_RELEASE_KEYS,
    reject_legacy_output_dir,
    reject_legacy_overrides,
    reject_runtime_settings,
    reject_unknown_keys,
)
from .validation_paths import require_structured_json_path, validate_output_json_path
from .validation_runtime import parse_runtime_settings
from ..runtime_semantic_assets import validate_release_payload
from ..taxonomy_sources import policy as source_policy


def require_action(payload: dict) -> ActionName:
    body = request_body(payload)
    action = value_parsing.required_string(body, "action")
    if action is None:
        raise ValueError("action fehlt oder ist ungueltig.")
    if action == BUILD_PROJECTION_CATALOG_ACTION:
        reject_unknown_keys(body, BUILD_PROJECTION_CATALOG_KEYS)
    if action in _KNOWN_ACTIONS:
        return action  # type: ignore[return-value]
    raise ValueError(f"Unbekannte Aktion: {action}")


def request_body(payload: dict) -> dict:
    if payload.get("schema_version") == "adapter.call_request.v1":
        inner = payload.get("request_payload")
        if isinstance(inner, dict):
            return inner
    return payload


def parse_normalize_document_command(payload: dict) -> NormalizeDocumentCommand:
    reject_legacy_overrides(payload)
    reject_legacy_output_dir(payload)
    reject_unknown_keys(payload, NORMALIZE_DOCUMENT_KEYS)
    structured_value = value_parsing.required_string(payload, "structured_path")
    output_value = value_parsing.required_string(payload, "normalized_output_path")
    if structured_value is None:
        raise ValueError("structured_path fehlt oder ist ungueltig.")
    if output_value is None:
        raise ValueError("normalized_output_path fehlt oder ist ungueltig.")
    command = NormalizeDocumentCommand(
        structured_path=value_parsing.required_path(payload, "structured_path"),
        normalized_output_path=value_parsing.required_path(payload, "normalized_output_path"),
        request_output_path=value_parsing.optional_path(payload.get("request_output_path")),
        runtime_settings=parse_runtime_settings(payload),
        release=validate_release_payload(payload.get("release")) if "release" in payload else None,
    )
    require_structured_json_path(command.structured_path, label="structured_path")
    if not command.structured_path.exists():
        raise ValueError(f"Structured JSON nicht gefunden: {command.structured_path}")
    if not command.structured_path.is_file():
        raise ValueError(f"Structured JSON muss eine Datei sein: {command.structured_path}")
    validate_output_json_path(command.normalized_output_path, label="normalized_output_path")
    if command.request_output_path is not None:
        validate_output_json_path(command.request_output_path, label="request_output_path")
    return command


def parse_healthcheck_command(payload: dict) -> HealthcheckCommand:
    reject_legacy_overrides(payload)
    reject_unknown_keys(payload, HEALTHCHECK_KEYS)
    return HealthcheckCommand(runtime_settings=parse_runtime_settings(payload))


def parse_publish_semantic_release_command(payload: dict) -> PublishSemanticReleaseCommand:
    reject_legacy_overrides(payload)
    reject_runtime_settings(payload, action="publish_semantic_release")
    reject_unknown_keys(payload, PUBLISH_SEMANTIC_RELEASE_KEYS)
    output_path = value_parsing.optional_path(payload.get("output_path"))
    if output_path is not None:
        validate_output_json_path(output_path, label="output_path")
    return PublishSemanticReleaseCommand(
        release_id=value_parsing.optional_non_empty_string(payload.get("release_id")),
        release_version=value_parsing.optional_non_empty_string(payload.get("release_version")),
        projection_ids=value_parsing.projection_ids(payload.get("projection_ids")),
        materialization_version=value_parsing.optional_non_empty_string(payload.get("materialization_version")),
        target_locale=_optional_locale(payload.get("target_locale")),
        output_path=output_path,
    )


def parse_build_runtime_semantic_assets_command(payload: dict) -> BuildRuntimeSemanticAssetsCommand:
    reject_legacy_overrides(payload)
    reject_runtime_settings(payload, action="build_runtime_semantic_assets")
    reject_unknown_keys(payload, BUILD_RUNTIME_SEMANTIC_ASSETS_KEYS)
    return BuildRuntimeSemanticAssetsCommand(release=validate_release_payload(payload.get("release")))


def parse_list_default_blueprints_command(payload: dict) -> None:
    reject_legacy_overrides(payload)
    reject_runtime_settings(payload, action="list_default_blueprints")
    reject_unknown_keys(payload, LIST_DEFAULT_BLUEPRINTS_KEYS)


def parse_export_default_blueprint_release_command(payload: dict) -> ExportDefaultBlueprintReleaseCommand:
    reject_legacy_overrides(payload)
    reject_runtime_settings(payload, action="export_default_blueprint_release")
    reject_unknown_keys(payload, EXPORT_DEFAULT_BLUEPRINT_RELEASE_KEYS)
    blueprint_ref = value_parsing.required_string(payload, "blueprint_ref")
    if blueprint_ref is None:
        raise ValueError("blueprint_ref fehlt oder ist ungueltig.")
    output_path = value_parsing.optional_path(payload.get("output_path"))
    if output_path is not None:
        validate_output_json_path(output_path, label="output_path")
    return ExportDefaultBlueprintReleaseCommand(
        blueprint_ref=blueprint_ref,
        target_locale=_optional_locale(payload.get("target_locale")),
        output_path=output_path,
    )


def parse_create_zero_shot_working_release_command(payload: dict) -> CreateZeroShotWorkingReleaseCommand:
    reject_legacy_overrides(payload)
    reject_runtime_settings(payload, action="create_zero_shot_working_release")
    reject_unknown_keys(payload, CREATE_ZERO_SHOT_WORKING_RELEASE_KEYS)
    blueprint_ref = value_parsing.required_string(payload, "blueprint_ref")
    if blueprint_ref is None:
        raise ValueError("blueprint_ref fehlt oder ist ungueltig.")
    output_path = value_parsing.optional_path(payload.get("output_path"))
    if output_path is not None:
        validate_output_json_path(output_path, label="output_path")
    return CreateZeroShotWorkingReleaseCommand(
        blueprint_ref=blueprint_ref,
        target_release_id=value_parsing.optional_non_empty_string(payload.get("target_release_id")),
        target_release_version=value_parsing.optional_non_empty_string(payload.get("target_release_version")),
        target_locale=_optional_locale(payload.get("target_locale")),
        output_path=output_path,
    )


def _optional_locale(value) -> str | None:
    return source_policy.require_locale(value, label="target_locale") if value not in (None, "") else None


_KNOWN_ACTIONS = {
    NORMALIZE_DOCUMENT_ACTION,
    BUILD_PROJECTION_CATALOG_ACTION,
    BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION,
    PUBLISH_SEMANTIC_RELEASE_ACTION,
    LIST_DEFAULT_BLUEPRINTS_ACTION,
    EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION,
    CREATE_ZERO_SHOT_WORKING_RELEASE_ACTION,
    HEALTHCHECK_ACTION,
    DEBUG_RUN_ACTION,
}
