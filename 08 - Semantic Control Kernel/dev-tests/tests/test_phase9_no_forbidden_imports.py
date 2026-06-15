from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_ROOTS = {
    "mcp_server",
    "corpus_builder",
    "normalizer_vision",
    "orchestrator",
    "ingestion_layer_vision",
    "llm_interpreter",
    "validator_vision",
    "openai",
    "anthropic",
    "google.generativeai",
}


def test_database_creation_package_has_no_forbidden_direct_imports() -> None:
    package = Path(__file__).resolve().parents[2] / "semantic_control_kernel" / "workflows" / "database_creation"
    offenders = []
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(name == root or name.startswith(f"{root}.") for root in FORBIDDEN_ROOTS):
                    offenders.append((path.name, name))
    assert offenders == []
