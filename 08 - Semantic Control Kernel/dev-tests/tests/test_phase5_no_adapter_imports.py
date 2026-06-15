from __future__ import annotations

import ast
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
SCAN_TARGETS = (
    MODULE_ROOT / "semantic_control_kernel" / "domain" / "state_machine",
    MODULE_ROOT / "semantic_control_kernel" / "policy" / "state_resolution.py",
    MODULE_ROOT / "semantic_control_kernel" / "policy" / "eligibility.py",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "semantic_control_kernel.adapters",
    "mcp_server",
    "corpus_builder",
    "normalizer_vision",
    "orchestrator",
    "ingestion_layer_vision",
    "llm_interpreter",
    "validator_vision",
)


def test_phase5_state_machine_and_policy_do_not_import_adapters_or_sibling_modules() -> None:
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported = _imported_name(node)
            if imported and imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
                offenders.append((path.relative_to(MODULE_ROOT).as_posix(), imported))

    assert offenders == []


def _python_files() -> tuple[Path, ...]:
    files = []
    for target in SCAN_TARGETS:
        if target.is_file():
            files.append(target)
        else:
            files.extend(sorted(target.glob("*.py")))
    return tuple(files)


def _imported_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.ImportFrom):
        return node.module
    if isinstance(node, ast.Import):
        return node.names[0].name if node.names else None
    return None
