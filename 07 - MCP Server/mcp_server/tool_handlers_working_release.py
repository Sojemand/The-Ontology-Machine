from __future__ import annotations

from .tool_handler_release_review_checkpoint import apply_safety_payload, record_review_checkpoint
from .tool_handler_deps import *


def read_working_release(arguments: dict[str, Any]) -> dict[str, Any]:
    return _working_release_read_action(_required_artifact_path(arguments), {"action": "read_release_package"})


def list_working_release_profiles(arguments: dict[str, Any]) -> dict[str, Any]:
    return _working_release_read_action(_required_artifact_path(arguments), {"action": "list_projections"})


def read_working_release_profile(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    return _working_release_read_action(
        artifact_path,
        {
            "action": "read_projection",
            "projection_id": _required_text(arguments, "projection_id"),
        },
    )


def validate_working_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    payload = {"action": "validate_release_package"}
    _add_optional_target_locale(payload, arguments)
    return _working_release_read_action(artifact_path, payload)


def compile_working_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    payload = {"action": "compile_release_package"}
    _add_optional_target_locale(payload, arguments)
    return _working_release_action(artifact_path, payload)


def preview_working_release_impact(arguments: dict[str, Any]) -> dict[str, Any]:
    return _working_release_read_action(_required_artifact_path(arguments), {"action": "preview_impact"})


def create_working_release_package(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    payload: dict[str, Any] = {"action": "create_release_package"}
    default_runtime_locale = _optional_locale_argument(arguments, "default_runtime_locale")
    projection_ids = _optional_string_list(arguments, "projection_ids")
    if default_runtime_locale:
        payload["default_runtime_locale"] = default_runtime_locale
    if projection_ids:
        payload["projection_ids"] = projection_ids
    return _working_release_action(artifact_path, payload)


def review_bootstrap_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    payload = _bootstrap_review_payload(arguments, action="review_bootstrap_release")
    result = _working_release_action(artifact_path, payload)
    checkpoint = record_review_checkpoint(artifact_path, workflow_kind="bootstrap", owner_payload=payload, result=result)
    if checkpoint:
        result["mcp_review_checkpoint"] = checkpoint
    return result


def apply_bootstrap_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    _require_user_confirmation(arguments)
    review_payload = _bootstrap_review_payload(arguments, action="review_bootstrap_release")
    payload = _bootstrap_review_payload(arguments, action="bootstrap_release_package")
    safety = apply_safety_payload(artifact_path, "bootstrap", review_payload, arguments)
    result = _working_release_action(artifact_path, payload)
    result["mcp_apply_safety"] = safety
    return result


def review_data_informed_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    payload = _data_informed_review_payload(arguments, action="review_data_informed_release")
    result = _working_release_action(artifact_path, payload)
    checkpoint = record_review_checkpoint(artifact_path, workflow_kind="data_informed", owner_payload=payload, result=result)
    if checkpoint:
        result["mcp_review_checkpoint"] = checkpoint
    return result


def refine_working_release_from_sample(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    _require_user_confirmation(arguments)
    review_payload = _data_informed_review_payload(arguments, action="review_data_informed_release")
    payload = _data_informed_review_payload(arguments, action="refine_release_package")
    safety = apply_safety_payload(artifact_path, "data_informed", review_payload, arguments)
    result = _working_release_action(artifact_path, payload)
    result["mcp_apply_safety"] = safety
    return result


def export_working_release(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _required_artifact_path(arguments)
    output_path = _required_text(arguments, "output_path")
    _validate_release_output_path(output_path)
    payload = {
        "action": "export_semantic_release",
        "output_path": output_path,
    }
    _add_optional_target_locale(payload, arguments)
    return _working_release_action(artifact_path, payload)


def _required_artifact_path(arguments: dict[str, Any]) -> Path:
    return Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()


def _bootstrap_review_payload(arguments: dict[str, Any], *, action: str) -> dict[str, Any]:
    return {
        "action": action,
        "goal": _required_text(arguments, "goal"),
        "must_keep": _required_text(arguments, "must_keep"),
        "noise_tolerance": _noise_tolerance(arguments),
    }


def _data_informed_review_payload(arguments: dict[str, Any], *, action: str) -> dict[str, Any]:
    payload = {
        "action": action,
        "structured_sample_path": _required_text(arguments, "structured_sample_path"),
        "expected_normalized_path": _required_text(arguments, "expected_normalized_path"),
    }
    for key in ("original_reference_path", "sample_label"):
        _add_optional(payload, arguments, key)
    return payload


def _noise_tolerance(arguments: dict[str, Any]) -> str:
    value = _required_text(arguments, "noise_tolerance").casefold()
    if value not in {"low", "medium", "high"}:
        raise ToolFailure("noise_tolerance muss low, medium oder high sein.")
    return value


def _require_user_confirmation(arguments: dict[str, Any]) -> None:
    if not _optional_bool(arguments, "user_confirmed", default=False):
        raise ToolFailure("user_confirmed=true ist fuer Apply-Tools erforderlich.")


def _working_release_action(artifact_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    result = _invoke_workspace_normalizer_edit(artifact_path, payload)
    return _working_release_result(artifact_path, result)


def _working_release_read_action(artifact_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    result = _invoke_workspace_normalizer_read(artifact_path, payload)
    return _working_release_result(artifact_path, result)


def _working_release_result(artifact_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    return {
        **result,
        "artifact_folder": str(artifact_path),
        "normalizer_authoring_home": str(_workspace_normalizer_home(artifact_path)),
        "authoring_scope": "workspace",
    }


def _add_optional_target_locale(payload: dict[str, Any], arguments: dict[str, Any]) -> None:
    target_locale = _optional_locale_argument(arguments, "target_locale")
    if target_locale:
        payload["target_locale"] = target_locale


__all__ = [name for name in globals() if not name.startswith("__")]
