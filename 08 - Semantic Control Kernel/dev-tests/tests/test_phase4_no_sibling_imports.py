from __future__ import annotations

import ast
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ROOT = MODULE_ROOT / "semantic_control_kernel" / "adapters"
FORBIDDEN_IMPORT_ROOTS = {
    "orchestrator",
    "ingestion_layer_vision",
    "llm_interpreter",
    "validator_vision",
    "normalizer_vision",
    "corpus_builder",
    "mcp_server",
}


def test_adapters_do_not_import_sibling_pipeline_packages() -> None:
    for path in ADAPTER_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORT_ROOTS, path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORT_ROOTS, path
