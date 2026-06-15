from __future__ import annotations

import ast
import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_IMPORT_TOKENS = (
    "mcp_server.semantic_kernel",
    "from .semantic_kernel",
    "tool_catalog_semantic_kernel",
    "tool_handlers_semantic_kernel",
    "KERNEL_TOOL_NAMES",
)
SCAN_EXCLUDES = {
    "mcp_server/semantic_control_kernel_legacy_constants.py",
    "mcp_server/semantic_control_kernel_legacy_inventory.py",
    "mcp_server/tool_catalog_semantic_kernel.py",
    "mcp_server/tool_handlers_semantic_kernel.py",
}
LEGACY_TEST_REWRITES = {
    "dev-tests/tests/test_agent_permissions.py",
    "dev-tests/tests/test_contract_healthcheck.py",
    "dev-tests/tests/test_protocol.py",
    "dev-tests/tests/test_tool_handlers_product_advisory.py",
    "dev-tests/tests/test_tool_subprocess_core.py",
    "dev-tests/tests/test_tool_contract_matrix_golden.py",
}
ALLOWED_DISPOSITIONS = {
    "rewrite_in_phase_15",
    "replace_with_new_phase14_or_phase15_test",
    "delete_in_phase_16",
    "keep_non_kernel_test_after_rewrite",
}


def test_active_mcp_product_files_do_not_import_old_kernel_surface() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((MODULE_ROOT / "mcp_server").rglob("*.py")):
        relative = path.relative_to(MODULE_ROOT).as_posix()
        if relative in SCAN_EXCLUDES or relative.startswith("mcp_server/semantic_kernel/"):
            continue
        text = path.read_text(encoding="utf-8")
        hits = [token for token in FORBIDDEN_IMPORT_TOKENS if token in text]
        if hits:
            offenders[relative] = hits
    assert offenders == {}


def test_bridge_files_do_not_directly_import_kernel_product_package() -> None:
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
    assert not any(name.startswith("semantic_control_kernel.") for name in imported)


def test_legacy_test_disposition_covers_all_old_kernel_tests_without_skip_harness() -> None:
    disposition_path = MODULE_ROOT / "migration" / "phase15_legacy_test_disposition.json"
    payload = json.loads(disposition_path.read_text(encoding="utf-8"))
    entries = {str(entry["path"]): entry for entry in payload["entries"]}
    expected_paths = {
        f"dev-tests/tests/{path.name}"
        for path in (MODULE_ROOT / "dev-tests" / "tests").glob("test_semantic_kernel*.py")
    } | LEGACY_TEST_REWRITES

    assert payload["schema_version"] == "mcp.phase15_legacy_test_disposition.v1"
    assert expected_paths <= set(entries)
    assert all(str(entry["disposition"]) in ALLOWED_DISPOSITIONS for entry in entries.values())

    conftest_text = (MODULE_ROOT / "dev-tests" / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert 'startswith("test_semantic_kernel_")' not in conftest_text
