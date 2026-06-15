from __future__ import annotations

import ast
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = MODULE_ROOT / "semantic_control_kernel"
FORBIDDEN_PREFIXES = (
    "mcp_server",
    "client_frontend",
    "llm_interpreter",
    "normalizer_vision",
    "corpus_builder",
    "orchestrator",
    "ingestion_layer_vision",
    "validator_vision",
    "openai",
    "anthropic",
)
ALLOWED_PROVIDER_BOUNDARIES = (
    PACKAGE_ROOT / "adapters" / "llm_adapter.py",
    PACKAGE_ROOT / "adapters" / "llm_provider",
)


def test_phase8_workflows_and_validators_do_not_import_forbidden_owners_or_provider_sdks() -> None:
    scanned_roots = [
        PACKAGE_ROOT / "workflows" / "llm_calls",
        PACKAGE_ROOT / "validation",
    ]
    violations = []
    for root in scanned_roots:
        for path in root.rglob("*.py"):
            if _allowed(path):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module_name = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if _is_forbidden(module_name):
                            violations.append((path, module_name))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module
                    if _is_forbidden(module_name):
                        violations.append((path, module_name))

    assert violations == []


def _is_forbidden(module_name: str) -> bool:
    return any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in FORBIDDEN_PREFIXES)


def _allowed(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    for boundary in ALLOWED_PROVIDER_BOUNDARIES:
        boundary_resolved = boundary.resolve(strict=False)
        if boundary_resolved.is_file() and resolved == boundary_resolved:
            return True
        if boundary_resolved.is_dir():
            try:
                resolved.relative_to(boundary_resolved)
                return True
            except ValueError:
                pass
    return False
