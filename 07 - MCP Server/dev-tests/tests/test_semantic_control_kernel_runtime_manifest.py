from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_manifest_includes_new_bridge_files_and_legacy_manifest_entries_are_inventoried() -> None:
    runtime_manifest = json.loads((MODULE_ROOT / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((MODULE_ROOT / "migration" / "phase14_legacy_cleanup_inventory.json").read_text(encoding="utf-8"))
    required = set(runtime_manifest["required_files"])
    inventory_paths = {str(item["path"]) for item in inventory["items"]}

    expected_new = {
        "mcp_server/semantic_control_kernel_client.py",
        "mcp_server/semantic_control_kernel_client_frontend_bridge.py",
        "mcp_server/semantic_control_kernel_legacy_inventory.py",
        "mcp_server/semantic_control_kernel_visibility.py",
        "mcp_server/tool_catalog_semantic_control_kernel.py",
        "mcp_server/tool_handlers_semantic_control_kernel.py",
        "config/semantic_control_kernel_bridge.json",
    }
    assert expected_new <= required

    for legacy_path in (
        "mcp_server/tool_catalog_semantic_kernel.py",
        "mcp_server/tool_handlers_semantic_kernel.py",
        "mcp_server/semantic_kernel/__init__.py",
    ):
        if legacy_path in required:
            assert any(path == legacy_path or path.startswith("mcp_server/semantic_kernel/") for path in inventory_paths)

