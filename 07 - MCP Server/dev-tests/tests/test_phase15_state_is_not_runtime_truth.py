from __future__ import annotations

import sys
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = Path(__file__).resolve().parents[3]
KERNEL_ROOT = PIPELINE_ROOT / "08 - Semantic Control Kernel"
if str(KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(KERNEL_ROOT))

from semantic_control_kernel.repository.paths import StatePaths  # noqa: E402


def test_phase15_state_policy_rejects_legacy_mcp_state_as_fixture() -> None:
    text = (MODULE_ROOT / "migration" / "phase15_legacy_state_policy.md").read_text(encoding="utf-8").casefold()

    for fragment in (
        "state/semantic_kernel",
        "events",
        "funnels",
        "locks",
        "sessions",
        ".store.lock",
        "no test or runtime path",
        "no longer expected",
        "not active runtime truth",
    ):
        assert fragment in text


def test_bridge_and_kernel_state_paths_do_not_use_legacy_mcp_kernel_state() -> None:
    bridge_files = (
        MODULE_ROOT / "mcp_server" / "semantic_control_kernel_client.py",
        MODULE_ROOT / "mcp_server" / "semantic_control_kernel_client_frontend_bridge.py",
        MODULE_ROOT / "mcp_server" / "semantic_control_kernel_visibility.py",
        MODULE_ROOT / "mcp_server" / "tool_handlers_semantic_control_kernel.py",
    )
    assert all("state/semantic_kernel" not in path.read_text(encoding="utf-8") for path in bridge_files)

    paths = StatePaths.from_module_root(KERNEL_ROOT)
    assert paths.state_root == KERNEL_ROOT / "state"
    assert "07 - MCP Server" not in str(paths.state_root)
