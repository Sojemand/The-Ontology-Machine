from __future__ import annotations

import re
from pathlib import Path

from mcp_server.semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES


MODULE_ROOT = Path(__file__).resolve().parents[2]
README_PATH = MODULE_ROOT / "README.md"
FORBIDDEN_PATTERNS = (
    r"llm_action_catalog",
    r"open_workflow",
    r"inspect_workflow",
    r"execute_.*workflow_action",
    r"interrupt_workflow",
    r"close_workflow",
    r"mcp_server/semantic_kernel",
    r"tool_catalog_semantic_kernel",
    r"tool_handlers_semantic_kernel",
    r"state/semantic_kernel",
)


def test_readme_uses_canonical_semantic_control_kernel_language_only() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    assert "Semantic Control Kernel" in text
    assert "Bridge" in text
    assert f"{len(PERMANENT_AGENT_TOOL_NAMES)} permanenten Semantic Control" in text
    assert "gemeinsame Kernel-Transport-Surface" in re.sub(r"\s+", " ", text)
    assert "Subprocess-Contract" in text
    assert all(re.search(pattern, text) is None for pattern in FORBIDDEN_PATTERNS)


def test_current_product_docs_use_canonical_semantic_control_kernel_name() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    assert "Semantic Control Kernel" in text
    assert "Semantic Runtime Kernel" not in text
