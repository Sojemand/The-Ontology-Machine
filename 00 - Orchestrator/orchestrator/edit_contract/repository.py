"""Repository helpers for orchestrator edit-contract surfaces."""

from __future__ import annotations

from .descriptor_metadata import descriptor_metadata
from ..policy_store import SURFACE_FILES, load_surface, validate_surface_value, write_surface

_LABELS = {
    "orchestrator.route_intake_policy": "Route Intake Policy",
    "orchestrator.execution_policy": "Execution Policy",
    "orchestrator.health_dependency_policy": "Health Dependency Policy",
    "orchestrator.artifact_publication_policy": "Artifact Publication Policy",
}


def surface_descriptor(surface_id: str) -> dict:
    descriptor = {
        "module_key": "orchestrator",
        "surface_id": surface_id,
        "label": _LABELS[surface_id],
        "kind": "policy",
        "owner": "orchestrator",
        "storage_kind": "json_file",
        "source_path": SURFACE_FILES[surface_id],
        "editable": True,
        "preview": ["json", "summary", "diff"],
        "operation_links": [],
        "runtime_impact": "next_run",
        "drift_status": "implicit_code_default",
        "section": "Settings",
        "validation": {"mode": "owner_contract", "fail_closed": True},
    }
    descriptor.update(descriptor_metadata(surface_id))
    return descriptor


def describe_surfaces() -> list[dict]:
    return [surface_descriptor(surface_id) for surface_id in SURFACE_FILES]


def read_policy(surface_id: str) -> dict:
    return load_surface(surface_id)


def validate_policy(surface_id: str, value: dict) -> dict:
    return validate_surface_value(surface_id, value)


def write_policy(surface_id: str, value: dict) -> dict:
    return write_surface(surface_id, value)
