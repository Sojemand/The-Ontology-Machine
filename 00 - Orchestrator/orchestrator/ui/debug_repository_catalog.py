"""Descriptor and picker helpers for the orchestrator debug-host tab."""

from __future__ import annotations

from ..debug_host import plan_for
from . import debug_module_catalog, debug_state_support

_INPUT_PICKERS = {
    "validator": {
        "file_title": "Select Structured Input File",
        "folder_title": "Select Structured Input Folder",
        "filetypes": (
            ("Structured JSON", "*.structured.json"),
            ("JSON", "*.json"),
            ("All files", "*.*"),
        ),
    },
    "normalizer": {
        "file_title": "Select Structured Input File",
        "folder_title": "Select Structured Input Folder",
        "filetypes": (
            ("Structured JSON", "*.structured.json"),
            ("JSON", "*.json"),
            ("All files", "*.*"),
        ),
    },
    "corpus_builder": {
        "file_title": "Select Normalized Input File",
        "folder_title": "Select Normalized/Artifact Folder",
        "filetypes": (
            ("Structured Normalized JSON", "*.structured.normalized.json"),
            ("JSON", "*.json"),
            ("All files", "*.*"),
        ),
    },
}


def descriptor_keys(app) -> list[str]:
    return debug_module_catalog.ordered_descriptor_keys(getattr(app, "_debug_descriptors", {}))


def module_menu_values(app) -> list[str]:
    return debug_module_catalog.menu_values(getattr(app, "_debug_descriptors", {}))


def module_label(app, module_key: object) -> str:
    return debug_module_catalog.label_for_key(module_key, getattr(app, "_debug_descriptors", {}))


def descriptor_for_module(app, module_key: str):
    descriptors = getattr(app, "_debug_descriptors", {})
    return descriptors.get(debug_module_catalog.key_for_value(module_key, descriptors))


def descriptor_for_state(app, state: dict[str, object]):
    return descriptor_for_module(app, str(state.get("module_key", "")))


def plan_for_state(app, state: dict[str, object], *, descriptor=None):
    current = descriptor or descriptor_for_state(app, state)
    if current is None:
        return None
    project_root = getattr(app, "_project_root", None)
    return plan_for(
        current.module_key,
        str(state.get("mode", "")),
        registry_path=(project_root / "module-registry.json") if project_root is not None else None,
    )


def default_module_key(app) -> str:
    keys = descriptor_keys(app)
    return keys[0] if keys else ""


def supported_modes(descriptor) -> tuple[str, ...]:
    if descriptor is None:
        return ("single",)
    modes: list[str] = []
    if descriptor.supports_scan:
        modes.append("scan")
    if descriptor.supports_single:
        modes.append("single")
    if descriptor.supports_batch:
        modes.append("batch")
    return tuple(modes or ("single",))


def supported_modes_for_module(app, module_key: str) -> tuple[str, ...]:
    return supported_modes(descriptor_for_module(app, module_key))


def default_mode_for_module(app, module_key: str) -> str:
    return supported_modes_for_module(app, module_key)[0]


def uses_module_selected_input(descriptor) -> bool:
    return bool(getattr(descriptor, "input_source", "") == "module_selected_input")


def input_picker_options(state: dict[str, object], *, descriptor=None) -> dict[str, object]:
    current = descriptor
    module_key = str(getattr(current, "module_key", "") or state.get("module_key", "")).strip()
    mode = debug_state_support.text_value(state.get("mode"))
    picker = _INPUT_PICKERS.get(module_key, {})
    select_file = bool(current is not None and uses_module_selected_input(current) and mode == "single")
    if select_file:
        return {
            "select_file": True,
            "title": str(picker.get("file_title") or "Select Debug Input File"),
            "filetypes": tuple(picker.get("filetypes") or (("All files", "*.*"),)),
        }
    return {
        "select_file": False,
        "title": str(picker.get("folder_title") or "Select Debug Input Folder"),
    }
