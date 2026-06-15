"""Owner-local read/write helpers for Normalizer edit surfaces."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..assets import (
    list_local_profiles,
    prompt_bundle_path,
    prompt_overrides_path,
)
from ..models import load_config
from ..models.serialization import atomic_json_write, atomic_text_write, load_json
from ..prompts import PROMPT_FIELDS, default_prompt_bundle_payload
from ..projection_routing.config import default_routing_settings, validate_routing_settings
from . import settings_surface, validation
from . import taxonomy_release_draft

_ACTION_LABELS = {
    "build_projection_catalog": "Build Projection Catalog",
}


def read_settings(module_root: Path) -> dict[str, Any]:
    config = load_config(module_root)
    routing = validate_routing_settings(_read_config_yaml(module_root).get("projection_routing", {}))
    return settings_surface.flatten_settings(config.to_dict(), routing)


def write_settings(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    validated = validation.validate_settings_payload(payload)
    current = _read_config_yaml(module_root)
    current.update({key: validated[key] for key in settings_surface.SETTINGS_FIELDS if key in validated and "." not in key})
    current["projection_routing"] = validation.routing_settings_from_flat(validated)
    _write_config_yaml(module_root, current)
    return read_settings(module_root)


def read_prompt_bundle(module_root: Path) -> dict[str, str]:
    payload = default_prompt_bundle_payload()
    path = prompt_bundle_path(module_root)
    if path.exists():
        payload = validation.validate_prompt_surface_payload(load_json(path), label="normalizer.prompt_bundle")
    return payload


def write_prompt_bundle(module_root: Path, payload: dict[str, Any]) -> dict[str, str]:
    validated = validation.validate_prompt_surface_payload(payload, label="normalizer.prompt_bundle")
    atomic_json_write(prompt_bundle_path(module_root), validated)
    return read_prompt_bundle(module_root)


def read_prompt_overrides(module_root: Path) -> dict[str, str]:
    path = prompt_overrides_path(module_root)
    if not path.exists():
        return {field_name: "" for field_name in PROMPT_FIELDS}
    raw = load_json(path)
    unknown = sorted(set(raw) - set(PROMPT_FIELDS))
    if unknown:
        raise ValueError(f"config/prompt_overrides.json enthaelt unbekannte Felder: {', '.join(unknown)}")
    payload = {field_name: "" for field_name in PROMPT_FIELDS}
    for field_name in PROMPT_FIELDS:
        if field_name not in raw:
            continue
        value = raw[field_name]
        if not isinstance(value, str):
            raise ValueError(f"{field_name} muss ein String sein.")
        payload[field_name] = value
    return payload


def write_prompt_overrides(module_root: Path, payload: dict[str, Any]) -> dict[str, str]:
    validated = validation.validate_prompt_surface_payload(payload, label="normalizer.prompt_overrides")
    delta_payload = {key: value for key, value in validated.items() if value.strip()}
    atomic_json_write(prompt_overrides_path(module_root), delta_payload)
    return read_prompt_overrides(module_root)


def read_taxonomy_release_draft(module_root: Path) -> dict[str, Any]:
    return taxonomy_release_draft.read_draft(module_root)


def write_taxonomy_release_draft(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return taxonomy_release_draft.write_draft(module_root, payload)


def read_debug_capabilities(module_root: Path) -> dict[str, Any]:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    operation_links = _operation_links(manifest)
    return {
        "module_key": str(manifest.get("module_key") or ""),
        "display_name": str(manifest.get("display_name") or ""),
        "contract_module": str(manifest.get("contract_module") or ""),
        "capabilities": dict(manifest.get("debug_surface") or {}),
        "actions": [link["action"] for link in operation_links],
        "operation_links": operation_links,
    }


def targeted_operation_links(module_root: Path, *actions: str) -> list[dict[str, Any]]:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    allowed = set(actions)
    return [link for link in _operation_links(manifest) if link["action"] in allowed]


def _operation_links(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    contract_module = str(manifest.get("contract_module") or "")
    actions = manifest.get("actions") or []
    return [
        {
            "action": action,
            "label": _ACTION_LABELS.get(action, action.replace("_", " ").title()),
            "contract_module": contract_module,
        }
        for action in actions
        if isinstance(action, str) and action.strip()
    ]


def _read_config_yaml(module_root: Path) -> dict[str, Any]:
    path = module_root / "config" / "config.yaml"
    if not path.exists():
        return {"projection_routing": default_routing_settings()}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config/config.yaml muss ein Objekt enthalten.")
    if "projection_routing" not in data:
        data["projection_routing"] = default_routing_settings()
    return data


def _write_config_yaml(module_root: Path, payload: dict[str, Any]) -> None:
    path = module_root / "config" / "config.yaml"
    atomic_text_write(path, yaml.safe_dump(payload, sort_keys=False))
