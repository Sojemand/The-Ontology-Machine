"""Workflow helpers for Corpus Builder edit-contract actions."""

from __future__ import annotations

from . import config_repository, repository
from .describe_surfaces import describe_surfaces
from .read_surface import read_surface
from .summary import build_module_summary
from .summary_cards import build_summary_cards
from .types import EMBEDDINGS_POLICY_SURFACE_ID, SEARCH_POLICY_SURFACE_ID, SETTINGS_SURFACE_ID
from .validate_surface import validate_surface
from .write_surface import write_surface


def error_response(message: str) -> dict:
    return {"status": "error", "reason": str(message)}


def describe(*, module_root, snapshot: dict | None = None) -> dict:
    snapshot = snapshot if snapshot is not None else _read_snapshot(module_root)
    return {
        "status": "ok",
        "surfaces": describe_surfaces(module_root=module_root, settings=snapshot["settings"]),
        "module_summary": build_module_summary(),
        "summary_cards": build_summary_cards(
            module_root=module_root,
            settings=snapshot["settings"],
            embeddings=snapshot["embeddings"],
            search=snapshot["search"],
            capabilities=snapshot["capabilities"],
        ),
    }


def read_bundle(*, module_root) -> dict:
    snapshot = _read_snapshot(module_root)
    described = describe(module_root=module_root, snapshot=snapshot)
    preloaded_surfaces = _snapshot_surfaces(snapshot)
    return _bundle_response(
        described,
        lambda surface_id: read_surface(
            surface_id,
            module_root=module_root,
            preloaded_surfaces=preloaded_surfaces,
        ),
    )


def read(surface_id: str, *, module_root) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": read_surface(surface_id, module_root=module_root)}


def validate(surface_id: str, value: dict, *, module_root) -> dict:
    return {
        "status": "ok",
        "surface_id": surface_id,
        "value": validate_surface(surface_id, value, module_root=module_root),
    }


def write(surface_id: str, value: dict, *, module_root) -> dict:
    validate_surface(surface_id, value, module_root=module_root)
    return {"status": "ok", "surface_id": surface_id, "value": write_surface(surface_id, value, module_root=module_root)}


def _read_snapshot(module_root) -> dict:
    config_surfaces = config_repository.read_config_surfaces(module_root)
    return {
        "settings": config_surfaces["settings"],
        "embeddings": config_surfaces["embeddings"],
        "search": repository.read_search_policy(module_root),
        "capabilities": repository.read_debug_capabilities(module_root),
    }


def _snapshot_surfaces(snapshot: dict) -> dict[str, dict]:
    return {
        SETTINGS_SURFACE_ID: snapshot["settings"],
        EMBEDDINGS_POLICY_SURFACE_ID: snapshot["embeddings"],
        SEARCH_POLICY_SURFACE_ID: snapshot["search"],
    }


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
