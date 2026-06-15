"""Workflow helpers for orchestrator edit-contract actions."""

from __future__ import annotations

from .describe_surfaces import describe_surfaces
from .read_surface import read_surface
from .summary import build_module_summary
from .summary_cards import build_summary_cards
from .validate_surface import validate_surface
from .write_surface import write_surface


def error_response(message: str) -> dict:
    return {"status": "error", "reason": str(message)}


def describe() -> dict:
    return {
        "status": "ok",
        "surfaces": describe_surfaces(),
        "module_summary": build_module_summary(),
        "summary_cards": build_summary_cards(),
    }


def read_bundle() -> dict:
    described = describe()
    return _bundle_response(described, read_surface)


def read(surface_id: str) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": read_surface(surface_id)}


def validate(surface_id: str, value: dict) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": validate_surface(surface_id, value)}


def write(surface_id: str, value: dict) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": write_surface(surface_id, value)}


def _bundle_response(described: dict, reader) -> dict:
    if described.get("status") != "ok":
        return described
    response = {
        "status": "ok",
        "module_summary": described.get("module_summary", ""),
        "surfaces": _bundle_surfaces(described.get("surfaces", ()), reader),
    }
    if "summary_cards" in described:
        response["summary_cards"] = described["summary_cards"]
    return response


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
