"""Fail-closed validation for orchestrator policy surfaces."""

from __future__ import annotations

from .types import (
    ARTIFACT_KEYS,
    ARTIFACT_PUBLICATION_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    MODULE_KEYS,
    OPERATION_NAMES,
    PIPELINE_STAGE_NAMES,
    ROUTE_FAMILIES,
    ROUTE_GROUP_KEYS,
    ROUTE_INTAKE_SURFACE_ID,
)


def validate_surface_value(surface_id: str, value: dict) -> dict:
    if surface_id == ROUTE_INTAKE_SURFACE_ID:
        return _validate_route_intake(value)
    if surface_id == EXECUTION_SURFACE_ID:
        return _validate_execution(value)
    if surface_id == HEALTH_DEPENDENCY_SURFACE_ID:
        return _validate_health_dependencies(value)
    if surface_id == ARTIFACT_PUBLICATION_SURFACE_ID:
        return _validate_artifact_publication(value)
    raise ValueError(f"Unknown surface: {surface_id}")


def _validate_route_intake(value: dict) -> dict:
    payload = _mapping(value, "route_intake_policy", ("route_families", "enabled_route_families", "unrouted_error_family", "suffix_groups", "pdf_classifications", "pdf_routing"))
    route_families = _string_list(payload["route_families"], "route_families")
    if route_families != list(ROUTE_FAMILIES):
        raise ValueError("route_families must be exactly ['Documents'].")
    enabled = _subset(_string_list(payload["enabled_route_families"], "enabled_route_families"), ROUTE_FAMILIES, "enabled_route_families")
    suffix_groups = _mapping(payload["suffix_groups"], "suffix_groups", ROUTE_GROUP_KEYS)
    pdf_classes = _mapping(payload["pdf_classifications"], "pdf_classifications", ("born_digital", "scan"))
    born = _exact_string(pdf_classes["born_digital"], "born_digital", "born_digital_pdf")
    scan = _exact_string(pdf_classes["scan"], "scan", "scan_pdf")
    pdf_routing = _mapping(payload["pdf_routing"], "pdf_routing", (born, scan))
    return {
        "route_families": route_families,
        "enabled_route_families": enabled,
        "unrouted_error_family": _text(payload["unrouted_error_family"], "unrouted_error_family"),
        "suffix_groups": {name: _suffix_value(suffix_groups[name], name) for name in ROUTE_GROUP_KEYS},
        "pdf_classifications": {"born_digital": born, "scan": scan},
        "pdf_routing": {
            born: _routing_entry(_mapping(pdf_routing[born], born, ("route_family", "optimizer_module_key", "interpreter_module_key")), born, ROUTE_FAMILIES, ("optimizer",), ("interpreter",)),
            scan: _routing_entry(_mapping(pdf_routing[scan], scan, ("route_family", "optimizer_module_key", "interpreter_module_key")), scan, ROUTE_FAMILIES, ("optimizer",), ("interpreter",)),
        },
    }


def _validate_execution(value: dict) -> dict:
    payload = _mapping(value, "execution_policy", ("pipeline_stage_names", "global_required_modules", "healthcheck_timeout_seconds", "projection_catalog_timeout_seconds", "modules", "operation_timeouts_seconds"))
    stages = _string_list(payload["pipeline_stage_names"], "pipeline_stage_names")
    if len(stages) != len(PIPELINE_STAGE_NAMES):
        raise ValueError(f"pipeline_stage_names must contain exactly {len(PIPELINE_STAGE_NAMES)} entries.")
    modules = _mapping(payload["modules"], "modules", MODULE_KEYS)
    timeouts = _mapping(payload["operation_timeouts_seconds"], "operation_timeouts_seconds", OPERATION_NAMES)
    return {
        "pipeline_stage_names": stages,
        "global_required_modules": _subset(_string_list(payload["global_required_modules"], "global_required_modules"), MODULE_KEYS, "global_required_modules"),
        "healthcheck_timeout_seconds": _positive_int(payload["healthcheck_timeout_seconds"], "healthcheck_timeout_seconds"),
        "projection_catalog_timeout_seconds": _positive_int(payload["projection_catalog_timeout_seconds"], "projection_catalog_timeout_seconds"),
        "modules": {module_key: _module_policy(modules[module_key], module_key, stages) for module_key in MODULE_KEYS},
        "operation_timeouts_seconds": {name: _positive_int(timeouts[name], f"operation_timeouts_seconds.{name}") for name in OPERATION_NAMES},
    }


def _validate_health_dependencies(value: dict) -> dict:
    payload = _mapping(value, "health_dependency_policy", ("scope_profiles", "fallback_for_other_scopes"))
    return {
        "scope_profiles": _scope_profiles(payload["scope_profiles"], "scope_profiles"),
        "fallback_for_other_scopes": _module_dependencies(payload["fallback_for_other_scopes"], "fallback_for_other_scopes"),
    }


def _validate_artifact_publication(value: dict) -> dict:
    payload = _mapping(value, "artifact_publication_policy", ("pipeline_state_dir_name", "run_workspace_dir_name", "route_folder_map", "error_root_name", "legacy_error_root_names", "route_artifact_subdirs", "publication_names", "request_file_names"))
    route_folder_map = _mapping(payload["route_folder_map"], "route_folder_map", ROUTE_FAMILIES)
    publication_names = _mapping(payload["publication_names"], "publication_names", ARTIFACT_KEYS)
    request_file_names = _mapping(
        payload["request_file_names"],
        "request_file_names",
        ("ocr_request", "interpreter_request", "normalizer_request"),
    )
    artifact_subdirs = _string_list(payload["route_artifact_subdirs"], "route_artifact_subdirs")
    if artifact_subdirs != list(ARTIFACT_KEYS):
        raise ValueError("route_artifact_subdirs must contain exactly the canonical publication keys.")
    return {
        "pipeline_state_dir_name": _text(payload["pipeline_state_dir_name"], "pipeline_state_dir_name"),
        "run_workspace_dir_name": _text(payload["run_workspace_dir_name"], "run_workspace_dir_name"),
        "route_folder_map": {name: _text(route_folder_map[name], f"route_folder_map.{name}") for name in ROUTE_FAMILIES},
        "error_root_name": _text(payload["error_root_name"], "error_root_name"),
        "legacy_error_root_names": _string_list(payload["legacy_error_root_names"], "legacy_error_root_names"),
        "route_artifact_subdirs": artifact_subdirs,
        "publication_names": {name: _text(publication_names[name], f"publication_names.{name}") for name in ARTIFACT_KEYS},
        "request_file_names": {name: _text(request_file_names[name], f"request_file_names.{name}") for name in ("ocr_request", "interpreter_request", "normalizer_request")},
    }

def _routing_entry(value: dict, label: str, routes: tuple[str, ...], optimizers: tuple[str, ...], interpreters: tuple[str, ...]) -> dict:
    return {
        "route_family": _one_of(_text(value["route_family"], f"{label}.route_family"), routes, f"{label}.route_family"),
        "optimizer_module_key": _one_of(_text(value["optimizer_module_key"], f"{label}.optimizer_module_key"), optimizers, f"{label}.optimizer_module_key"),
        "interpreter_module_key": _one_of(_text(value["interpreter_module_key"], f"{label}.interpreter_module_key"), interpreters, f"{label}.interpreter_module_key"),
    }

def _module_policy(value: dict, module_key: str, stage_names: list[str]) -> dict:
    payload = _mapping(value, module_key, ("display_name", "stage_role", "required_actions"))
    return {"display_name": _text(payload["display_name"], f"{module_key}.display_name"), "stage_role": _one_of(_text(payload["stage_role"], f"{module_key}.stage_role"), tuple(stage_names), f"{module_key}.stage_role"), "required_actions": _string_list(payload["required_actions"], f"{module_key}.required_actions")}

def _scope_profiles(value: object, label: str) -> dict:
    profiles = _dict(value, label)
    return {scope: _module_dependencies(scope_map, f"{label}.{scope}") for scope, scope_map in profiles.items()}

def _module_dependencies(value: object, label: str) -> dict[str, dict[str, list[str]]]:
    modules = _dict(value, label)
    for module_key in modules:
        if module_key not in MODULE_KEYS:
            raise ValueError(f"{label}.{module_key} is invalid.")
    return {
        module_key: {
            suffix: _string_list(dependencies, f"{label}.{module_key}.{suffix}")
            for suffix, dependencies in _dict(module_map, f"{label}.{module_key}").items()
        }
        for module_key, module_map in modules.items()
    }

def _mapping(value: object, label: str, keys: tuple[str, ...]) -> dict:
    payload = _dict(value, label)
    if tuple(payload) != tuple(keys):
        raise ValueError(f"{label} contains unexpected or incorrectly sorted fields.")
    return payload

def _dict(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value

def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list.")
    items, seen = [], set()
    for item in value:
        text = _text(item, label)
        if text in seen:
            raise ValueError(f"{label} contains duplicate entries.")
        items.append(text)
        seen.add(text)
    return items

def _suffix_value(value: object, name: str) -> list[str]:
    items = _suffix_list(value, f"suffix_groups.{name}")
    if name == "pdf" and len(items) != 1:
        raise ValueError("suffix_groups.pdf must contain exactly one suffix.")
    return items

def _suffix_list(value: object, label: str) -> list[str]:
    items = _string_list(value, label)
    if any(not item.startswith(".") for item in items):
        raise ValueError(f"{label} contains invalid suffixes.")
    return items

def _subset(items: list[str], allowed: tuple[str, ...], label: str) -> list[str]:
    invalid = [item for item in items if item not in allowed]
    if invalid:
        raise ValueError(f"{label} contains invalid entries: {', '.join(invalid)}")
    return items

def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()

def _one_of(value: str, allowed: tuple[str, ...], label: str) -> str:
    if value not in allowed:
        raise ValueError(f"{label} contains an invalid value: {value}")
    return value

def _exact_string(value: object, label: str, expected: str) -> str:
    text = _text(value, label)
    if text != expected:
        raise ValueError(f"{label} must be exactly {expected}.")
    return text


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer.")
    return value


def _bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be true or false.")
    return value
