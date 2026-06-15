from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_manifest_no_longer_packages_legacy_kernel_payload() -> None:
    manifest = json.loads((MODULE_ROOT / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    required = set(manifest["required_files"])

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
    assert "mcp_server/tool_catalog_semantic_kernel.py" not in required
    assert "mcp_server/tool_handlers_semantic_kernel.py" not in required
    assert not any(path.startswith("mcp_server/semantic_kernel/") for path in required)
