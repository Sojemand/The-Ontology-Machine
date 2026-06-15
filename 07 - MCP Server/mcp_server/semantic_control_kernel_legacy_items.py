from __future__ import annotations

from pathlib import Path
from typing import Any

from .semantic_control_kernel_legacy_constants import (
    LEGACY_CATALOG_FILE,
    LEGACY_HANDLERS_FILE,
    LEGACY_PACKAGE_DIR,
    LEGACY_STATE_DIR,
)


def item_for(root: Path, path: Path, matches: list[str]) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    if relative.startswith(LEGACY_PACKAGE_DIR):
        return item(relative, "source_file", matches, "legacy_old_kernel_surface", "hidden", "delete_in_phase_16", 16, "Phase 14 cut over to the Semantic Control Kernel bridge.", None)
    if relative == LEGACY_CATALOG_FILE:
        return item(relative, "catalog_file", matches, "legacy_old_kernel_surface", "hidden", "delete_in_phase_16", 16, "Legacy Kernel catalog is retired.", "mcp_server/tool_catalog_semantic_control_kernel.py")
    if relative == LEGACY_HANDLERS_FILE:
        return item(relative, "handler_file", matches, "legacy_old_kernel_surface", "hidden", "delete_in_phase_16", 16, "Legacy Kernel handlers are retired.", "mcp_server/tool_handlers_semantic_control_kernel.py")
    if relative == "mcp_server/tool_catalog.py":
        return item(relative, "registry_import", matches, "legacy_old_kernel_surface", "visible", "rewrite_in_phase_15", 15, "Top-level catalog still references legacy Kernel symbols.", "mcp_server/tool_catalog_semantic_control_kernel.py")
    if relative == "mcp_server/tool_handler_registry.py":
        return item(relative, "registry_entry", matches, "legacy_old_kernel_surface", "visible", "rewrite_in_phase_15", 15, "Handler registry still references legacy Kernel symbols.", "mcp_server/tool_handlers_semantic_control_kernel.py")
    if relative == "mcp_server/tool_visibility.py":
        return item(relative, "registry_import", matches, "legacy_old_kernel_surface", "visible", "rewrite_in_phase_15", 15, "Visibility layer still references legacy Kernel symbols.", "mcp_server/semantic_control_kernel_visibility.py")
    if relative == "mcp_server/permission_defaults.py":
        return item(relative, "permission_default_entry", matches, "legacy_permission_execute_model", "visible", "rewrite_in_phase_15", 15, "Legacy level-split execute model must be removed.", "config/agent_permissions.json")
    if relative == "config/agent_permissions.json":
        return item(relative, "permission_config_entry", matches, "legacy_permission_execute_model", "visible", "rewrite_in_phase_15", 15, "Legacy Kernel tool permissions must be removed.", "mcp_server/permission_defaults.py")
    if relative == "runtime/runtime-manifest.json":
        return item(relative, "runtime_manifest_entry", matches, "legacy_runtime_payload", "visible", "rewrite_in_phase_15", 15, "Runtime manifest still includes legacy Kernel payload.", "mcp_server/semantic_control_kernel_client.py")
    if relative == "README.md":
        return item(relative, "readme_section", matches, "legacy_workflow_family_reference", "visible", "rewrite_in_phase_15", 15, "README still references legacy Kernel routing semantics.", "migration/phase14_mcp_cutover.md")
    if relative.startswith("mcp_server/product_semantics"):
        return item(relative, "product_semantics_reference", matches, "legacy_workflow_family_reference", "visible", "rewrite_in_phase_15", 15, "Product semantics still mention workflow-family routing.", None)
    if relative.startswith("dev-tests/tests/"):
        return item(relative, "test_file", matches, "legacy_old_kernel_surface", "visible", "rewrite_in_phase_15", 15, "Legacy Kernel tests still reference retired surfaces.", None)
    if relative.startswith(LEGACY_STATE_DIR):
        return item(relative, "state_path", matches, "legacy_runtime_payload", "hidden", "archive_or_ignore_state", 15, "Legacy Kernel runtime state remains on disk for audit only.", None)
    return item(relative, "generated_artifact", matches, "generated_ignore", "hidden", "no_action_generated_artifact", 15, "Legacy symbol appears in generated or incidental artifact.", None)


def item(
    path: str,
    item_type: str,
    legacy_symbols: list[str],
    classification: str,
    status_after_phase14: str,
    required_action: str,
    owner_phase: int,
    reason: str,
    replacement: str | None,
) -> dict[str, Any]:
    return {
        "path": path,
        "item_type": item_type,
        "legacy_symbols": legacy_symbols,
        "classification": classification,
        "status_after_phase14": status_after_phase14,
        "required_action": required_action,
        "owner_phase": owner_phase,
        "reason": reason,
        "test_refs": [
            "test_semantic_control_kernel_legacy_inventory.py",
            "test_semantic_control_kernel_legacy_invisibility.py",
        ],
        "replacement": replacement,
    }


def synthetic_required_symbol_item(missing_symbols: list[str]) -> dict[str, Any]:
    return item(
        LEGACY_CATALOG_FILE,
        "catalog_file",
        missing_symbols,
        "legacy_old_kernel_surface",
        "hidden",
        "delete_in_phase_16",
        16,
        "Required retired Kernel symbols must remain explicitly inventoried even after live source cleanup stops mentioning them verbatim.",
        "mcp_server/tool_catalog_semantic_control_kernel.py",
    )
