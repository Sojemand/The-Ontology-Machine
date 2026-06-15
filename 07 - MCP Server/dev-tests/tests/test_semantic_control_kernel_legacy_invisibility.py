from __future__ import annotations

import ast
from pathlib import Path

from mcp_server.permissions import visible_tool_definitions
from mcp_server.semantic_control_kernel_visibility import LEGACY_RETIRED_TOOL_NAMES, PERMANENT_AGENT_TOOL_NAMES
from mcp_server.tool_catalog import tool_definitions


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_legacy_public_names_are_absent_from_catalog_visibility_and_false_friend_aliases() -> None:
    catalog_names = {str(tool["name"]) for tool in tool_definitions()}
    visible_names = {str(tool["name"]) for tool in visible_tool_definitions()}

    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(catalog_names)
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(visible_names)
    assert {
        "inspect_active_corpus",
        "activation_preflight",
        "semantic_audit",
        "activate_release_on_existing_db",
        "merge_corpora",
        "rebuild_corpus_from_artifacts",
    }.isdisjoint(PERMANENT_AGENT_TOOL_NAMES)


def test_new_bridge_modules_do_not_import_legacy_kernel_package_or_kernel_product_package() -> None:
    bridge_files = (
        MODULE_ROOT / "mcp_server" / "semantic_control_kernel_client.py",
        MODULE_ROOT / "mcp_server" / "semantic_control_kernel_client_frontend_bridge.py",
        MODULE_ROOT / "mcp_server" / "semantic_control_kernel_visibility.py",
        MODULE_ROOT / "mcp_server" / "tool_catalog_semantic_control_kernel.py",
        MODULE_ROOT / "mcp_server" / "tool_handlers_semantic_control_kernel.py",
    )
    imported: list[str] = []
    for path in bridge_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)

    assert not any(name.startswith("mcp_server.semantic_kernel") for name in imported)
    assert not any(name.startswith("semantic_control_kernel.") for name in imported)

