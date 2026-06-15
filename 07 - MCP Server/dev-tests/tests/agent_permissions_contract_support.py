from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mcp_server import permissions
from mcp_server.tool_visibility import is_externally_visible_tool
from mcp_server.tools import tool_definitions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COPYTREE_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "07 - MCP Server"
    shutil.copytree(PROJECT_ROOT / "mcp_server", module_root / "mcp_server", ignore=COPYTREE_IGNORE)
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config", ignore=COPYTREE_IGNORE)
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    bridge_config_path = module_root / "config" / "semantic_control_kernel_bridge.json"
    bridge_config = json.loads(bridge_config_path.read_text(encoding="utf-8"))
    bridge_config["semantic_control_kernel"]["module_root"] = str(PROJECT_ROOT.parent / "08 - Semantic Control Kernel")
    bridge_config_path.write_text(json.dumps(bridge_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return module_root


def expected_visible_names(policy: dict[str, object], level: str) -> set[str]:
    allowed = permissions.tools_for_level(policy, level)
    return {
        str(tool["name"])
        for tool in tool_definitions()
        if str(tool["name"]) in allowed and is_externally_visible_tool(str(tool["name"]))
    }


def invoke_contract(module_root: Path, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = dict(os.environ)
    env["SEMANTIC_CONTROL_KERNEL_MODULE_ROOT"] = str(PROJECT_ROOT.parent / "08 - Semantic Control Kernel")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mcp_server.edit_contract",
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=module_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))
