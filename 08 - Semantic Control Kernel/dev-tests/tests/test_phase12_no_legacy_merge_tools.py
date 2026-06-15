from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN = (
    "mcp_server.semantic_kernel",
    "tool_catalog_semantic_kernel",
    "tool_handlers_semantic_kernel",
    "llm_action_catalog",
    "open_workflow",
    "inspect_workflow",
    "execute_readonly_workflow_action",
    "execute_author_workflow_action",
    "execute_operator_workflow_action",
    "execute_admin_workflow_action",
    "workflow_family_id",
    "action_token",
    "target_action_id",
    "merge_corpora",
)


def test_phase12_workflow_code_has_no_legacy_merge_tools() -> None:
    module_root = Path(__file__).resolve().parents[2]
    paths = list((module_root / "semantic_control_kernel" / "workflows" / "merge").glob("*.py"))
    paths += list((module_root / "semantic_control_kernel" / "workflows" / "rebuild").glob("*.py"))
    paths += [
        module_root / "semantic_control_kernel" / "adapters" / "merge.py",
        module_root / "semantic_control_kernel" / "policy" / "merge_policy.py",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        assert not any(item.startswith("mcp_server.semantic_kernel") for item in imported), path
        for token in FORBIDDEN:
            assert token not in text, (path, token)
