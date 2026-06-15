"""Path-stable accessors for orchestrator policy surfaces."""

from .types import (
    ARTIFACT_PUBLICATION_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    ROUTE_INTAKE_SURFACE_ID,
    SURFACE_FILES,
    SURFACE_IDS,
)


def _repository():
    from . import repository
    return repository


def _validated(surface_id: str) -> dict:
    return _repository().load_surface(surface_id)


def invalidate_cache(surface_id: str | None = None) -> None:
    _repository().invalidate_cache(surface_id)


def load_surface(surface_id: str) -> dict:
    return _validated(surface_id)


def write_surface(surface_id: str, value: dict) -> dict:
    return _repository().write_surface(surface_id, value)


def surface_path(surface_id: str):
    return _repository().surface_path(surface_id)


def load_route_intake_policy() -> dict:
    return _validated(ROUTE_INTAKE_SURFACE_ID)


def load_execution_policy() -> dict:
    return _validated(EXECUTION_SURFACE_ID)


def load_health_dependency_policy() -> dict:
    return _validated(HEALTH_DEPENDENCY_SURFACE_ID)


def load_artifact_publication_policy() -> dict:
    return _validated(ARTIFACT_PUBLICATION_SURFACE_ID)


def validate_surface_value(surface_id: str, value: dict) -> dict:
    from .validation import validate_surface_value as _validate_surface_value
    return _validate_surface_value(surface_id, value)


def route_families() -> tuple[str, ...]:
    return tuple(load_route_intake_policy()["route_families"])


def enabled_route_families() -> tuple[str, ...]:
    return tuple(load_route_intake_policy()["enabled_route_families"])


def unrouted_error_family() -> str:
    return str(load_route_intake_policy()["unrouted_error_family"])


def suffix_groups() -> dict[str, list[str]]:
    return load_route_intake_policy()["suffix_groups"]


def image_suffixes() -> tuple[str, ...]:
    return tuple(suffix_groups()["images"])


def file_suffixes() -> tuple[str, ...]:
    return tuple(suffix_groups()["files"])


def pdf_suffix() -> str:
    return str(suffix_groups()["pdf"][0])


def pdf_classification(label: str) -> str:
    return str(load_route_intake_policy()["pdf_classifications"][label])


def pdf_route(classification: str) -> dict[str, str]:
    return load_route_intake_policy()["pdf_routing"][classification]


def pipeline_stage_names() -> tuple[str, ...]:
    return tuple(load_execution_policy()["pipeline_stage_names"])


def global_required_modules() -> tuple[str, ...]:
    return tuple(load_execution_policy()["global_required_modules"])


def default_module_keys() -> tuple[str, ...]:
    return tuple(load_execution_policy()["modules"])


def modules_policy() -> dict[str, dict[str, object]]:
    return load_execution_policy()["modules"]


def module_policy(module_key: str) -> dict[str, object]:
    return modules_policy()[module_key]


def required_actions_by_module_policy() -> dict[str, tuple[str, ...]]:
    return {module_key: tuple(str(action) for action in payload["required_actions"]) for module_key, payload in modules_policy().items()}


def healthcheck_timeout_seconds() -> int:
    return int(load_execution_policy()["healthcheck_timeout_seconds"])


def projection_catalog_timeout_seconds() -> int:
    return int(load_execution_policy()["projection_catalog_timeout_seconds"])


def operation_timeout_seconds(operation_name: str) -> int:
    return int(load_execution_policy()["operation_timeouts_seconds"][operation_name])


def dependency_scope_profile(scope: str) -> dict[str, dict[str, list[str]]]:
    return load_health_dependency_policy()["scope_profiles"].get(scope, {})


def fallback_dependency_profile() -> dict[str, dict[str, list[str]]]:
    return load_health_dependency_policy()["fallback_for_other_scopes"]


def pipeline_state_dir_name() -> str:
    return str(load_artifact_publication_policy()["pipeline_state_dir_name"])


def run_workspace_dir_name() -> str:
    return str(load_artifact_publication_policy()["run_workspace_dir_name"])


def route_folder_map() -> dict[str, str]:
    return load_artifact_publication_policy()["route_folder_map"]


def error_root_name() -> str:
    return str(load_artifact_publication_policy()["error_root_name"])


def legacy_error_root_names() -> tuple[str, ...]:
    return tuple(load_artifact_publication_policy()["legacy_error_root_names"])


def route_artifact_subdirs() -> tuple[str, ...]:
    return tuple(load_artifact_publication_policy()["route_artifact_subdirs"])


def publication_names() -> dict[str, str]:
    return load_artifact_publication_policy()["publication_names"]


def publication_name(key: str) -> str:
    return str(publication_names()[key])


def request_file_name(key: str) -> str:
    return str(load_artifact_publication_policy()["request_file_names"][key])


__all__ = [
    "ARTIFACT_PUBLICATION_SURFACE_ID", "EXECUTION_SURFACE_ID", "HEALTH_DEPENDENCY_SURFACE_ID", "ROUTE_INTAKE_SURFACE_ID",
    "SURFACE_FILES", "SURFACE_IDS", "default_module_keys", "dependency_scope_profile", "enabled_route_families",
    "error_root_name", "fallback_dependency_profile", "file_suffixes", "global_required_modules",
    "healthcheck_timeout_seconds", "image_suffixes", "invalidate_cache", "legacy_error_root_names",
    "load_artifact_publication_policy", "load_execution_policy", "load_health_dependency_policy",
    "load_route_intake_policy", "load_surface", "module_policy", "modules_policy", "operation_timeout_seconds",
    "pdf_classification", "pdf_route", "pdf_suffix", "pipeline_stage_names", "pipeline_state_dir_name",
    "projection_catalog_timeout_seconds", "publication_name", "publication_names", "request_file_name",
    "required_actions_by_module_policy", "route_artifact_subdirs", "route_families", "route_folder_map",
    "run_workspace_dir_name", "surface_path", "suffix_groups",
    "unrouted_error_family", "validate_surface_value", "write_surface",
]
