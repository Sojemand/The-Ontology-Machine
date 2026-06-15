from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_manifest_and_module_manifest_are_clean_of_deleted_legacy_kernel_payload() -> None:
    runtime_manifest = json.loads((MODULE_ROOT / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    module_manifest = json.loads((MODULE_ROOT / "module-manifest.json").read_text(encoding="utf-8"))
    required = {str(item).replace("\\", "/") for item in runtime_manifest["required_files"]}
    module_manifest_text = json.dumps(module_manifest, ensure_ascii=True)

    assert "mcp_server/tool_catalog_semantic_kernel.py" not in required
    assert "mcp_server/tool_handlers_semantic_kernel.py" not in required
    assert not any(path.startswith("mcp_server/semantic_kernel/") for path in required)
    assert "tool_catalog_semantic_kernel" not in module_manifest_text
    assert "tool_handlers_semantic_kernel" not in module_manifest_text
    assert "mcp_server.semantic_kernel" not in module_manifest_text
