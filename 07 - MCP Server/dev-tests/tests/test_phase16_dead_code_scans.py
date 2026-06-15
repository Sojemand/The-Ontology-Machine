from __future__ import annotations

import re
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SCAN_ROOTS = (
    MODULE_ROOT / "mcp_server",
    MODULE_ROOT / "config",
    MODULE_ROOT / "runtime",
    MODULE_ROOT / "README.md",
    MODULE_ROOT / "module-manifest.json",
)
LEGACY_PATHS = (
    MODULE_ROOT / "mcp_server" / "semantic_kernel",
    MODULE_ROOT / "mcp_server" / "tool_catalog_semantic_kernel.py",
    MODULE_ROOT / "mcp_server" / "tool_handlers_semantic_kernel.py",
    MODULE_ROOT / "dev-tests" / "tests" / "semantic_kernel_spec_helpers.py",
)
FORBIDDEN_PATTERNS = (
    r"mcp_server\.semantic_kernel",
    r"from \.semantic_kernel",
    r"mcp_server/semantic_kernel",
    r"tool_catalog_semantic_kernel",
    r"tool_handlers_semantic_kernel",
    r"KERNEL_TOOL_NAMES",
    r"llm_action_catalog",
    r"open_workflow",
    r"inspect_workflow",
    r"execute_.*workflow_action",
    r"interrupt_workflow",
    r"close_workflow",
    r"workflow_family_id",
    r"workflow_revision",
    r"action_token",
    r"recommended_first_workflow_family_id",
    r"related_workflow_family_ids",
    r"safe_next_kernel_workflows",
    r"suggested_next_workflow_family_id",
    r"safe_next_workflow_family_id",
    r"next_workflow_family_id",
    r"state/semantic_kernel",
)
TEXT_SUFFIXES = {".py", ".json", ".jsonl", ".md", ".txt", ".ini", ".bat", ".js", ".ts"}
GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".venv", "venv"}


def test_deleted_legacy_paths_and_old_semantic_kernel_tests_are_gone() -> None:
    assert all(not path.exists() for path in LEGACY_PATHS)
    assert list((MODULE_ROOT / "dev-tests" / "tests").glob("test_semantic_kernel*.py")) == []


def test_active_product_runtime_and_readme_paths_have_no_legacy_kernel_strings() -> None:
    hits: dict[str, list[str]] = {}
    for root in PRODUCT_SCAN_ROOTS:
        for path in _iter_text_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            matched = [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, text)]
            if matched:
                hits[path.relative_to(MODULE_ROOT).as_posix()] = matched
    assert hits == {}


def _iter_text_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in GENERATED_DIRS for part in path.parts):
            continue
        yield path
