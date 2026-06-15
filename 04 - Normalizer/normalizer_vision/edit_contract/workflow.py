"""Workflow helpers for Normalizer edit-contract actions."""
from __future__ import annotations

from .describe_surfaces import describe_surfaces
from .read_surface import read_surface
from .summary import build_module_summary
from .validate_surface import validate_surface
from .write_surface import write_surface
from .types import DEBUG_CAPABILITIES_SURFACE_ID


def error_response(message: str) -> dict:
    return {"status": "error", "reason": str(message)}


def describe(*, module_root) -> dict:
    surfaces = describe_surfaces(module_root)
    debug_value = read_surface(DEBUG_CAPABILITIES_SURFACE_ID, module_root=module_root)
    for descriptor in surfaces:
        if descriptor["surface_id"] == DEBUG_CAPABILITIES_SURFACE_ID:
            descriptor["operation_links"] = list(debug_value["operation_links"])
    return {"status": "ok", "surfaces": surfaces, "module_summary": build_module_summary()}


def read_bundle(*, module_root) -> dict:
    described = describe(module_root=module_root)
    return _bundle_response(described, lambda surface_id: read_surface(surface_id, module_root=module_root))


def read(surface_id: str, *, module_root) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": read_surface(surface_id, module_root=module_root)}


def validate(surface_id: str, value: dict, *, module_root) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": validate_surface(surface_id, value, module_root=module_root)}


def write(surface_id: str, value: dict, *, module_root) -> dict:
    validate_surface(surface_id, value, module_root=module_root)
    return {"status": "ok", "surface_id": surface_id, "value": write_surface(surface_id, value, module_root=module_root)}


def _bundle_response(described: dict, reader) -> dict:
    if described.get("status") != "ok":
        return described
    return {
        "status": "ok",
        "module_summary": described.get("module_summary", ""),
        "summary_cards": described.get("summary_cards", []),
        "surfaces": _bundle_surfaces(described.get("surfaces", ()), reader),
    }


def _bundle_surfaces(descriptors, reader) -> list[dict]:
    surfaces = []
    for descriptor in descriptors:
        item = dict(descriptor)
        try:
            item["value"] = reader(str(item.get("surface_id") or ""))
        except Exception as exc:
            item["load_error"] = str(exc)
        surfaces.append(item)
    return surfaces
