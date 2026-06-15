from __future__ import annotations

import ast
import json
from pathlib import Path

from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_NAMES


MODULE_ROOT = Path(__file__).resolve().parents[2]
PHASE_WRITE_SCOPE = (
    "README.md",
    "module-manifest.json",
    "requirements.txt",
    "runtime",
    "dev-tests",
    "semantic_control_kernel",
    "config",
    "state",
    "tools",
    "SPEC_Semantic_Control_Kernel_Build.md",
)


def _read_text(relative_path: str) -> str:
    return (MODULE_ROOT / relative_path).read_text(encoding="utf-8")


def _load_json(relative_path: str) -> dict[str, object]:
    with (MODULE_ROOT / relative_path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def test_phase0_required_scaffold_paths_exist() -> None:
    required_paths = (
        "README.md",
        "SPEC_Semantic_Control_Kernel_Build.md",
        "module-manifest.json",
        "requirements.txt",
        "build-runtime.bat",
        "check-runtime.bat",
        "semantic_control_kernel",
        "runtime",
        "config",
        "state",
        "tools",
        "dev-tests",
        "semantic_control_kernel/__init__.py",
        "semantic_control_kernel/__main__.py",
        "semantic_control_kernel/README.md",
        "semantic_control_kernel/orchestrator_contract.py",
        "semantic_control_kernel/bootstrap/__init__.py",
        "semantic_control_kernel/bootstrap/runtime_report.py",
        "runtime/README.md",
        "runtime/runtime-manifest.json",
        "config/README.md",
        "state/README.md",
        "tools/README.md",
        "dev-tests/README.md",
        "dev-tests/suite.json",
        "dev-tests/bootstrap.bat",
        "dev-tests/run-tests.bat",
        "dev-tests/pytest.ini",
        "dev-tests/requirements.lock.txt",
    )

    missing = [path for path in required_paths if not (MODULE_ROOT / path).exists()]
    assert missing == []


def test_phase0_scaffold_directories_have_placeholders() -> None:
    scaffold_dirs = (
        "semantic_control_kernel",
        "runtime",
        "runtime/python",
        "config",
        "state",
        "tools",
        "dev-tests",
        "dev-tests/tests",
    )

    empty_dirs = [
        path
        for path in scaffold_dirs
        if not any((MODULE_ROOT / path).iterdir())
    ]
    assert empty_dirs == []


def test_manifest_matches_active_module_contract() -> None:
    manifest = _load_json("module-manifest.json")

    assert manifest["module_key"] == "semantic_control_kernel"
    assert manifest["module_archetype"] == "control_module"
    assert manifest["status"] == "agent_surface_shell"
    assert manifest["contract_version"] == 1
    assert manifest["runtime_dir"] == "runtime/python"
    assert manifest["contract_module"] == "semantic_control_kernel.orchestrator_contract"
    assert tuple(manifest["actions"]) == PERMANENT_AGENT_TOOL_NAMES


def test_runtime_manifest_matches_active_module_contract() -> None:
    runtime_manifest = _load_json("runtime/runtime-manifest.json")

    assert runtime_manifest["status"] == "agent_surface_shell"
    assert runtime_manifest["contract_version"] == 1
    assert runtime_manifest["build_status"] == "buildable"
    assert runtime_manifest["normal_operation_requires_host_python"] is False


def test_readme_contains_current_surface_status_facts() -> None:
    readme = _read_text("README.md")

    assert "Current manifest status value: `agent_surface_shell`." in readme
    assert "Phase 9 through Phase 19 workflow and adapter" in readme
    assert "Phase 20 handoff evidence is written under" in readme


def test_orchestrator_contract_exposes_no_workflow_actions() -> None:
    contract_path = MODULE_ROOT / "semantic_control_kernel" / "orchestrator_contract.py"
    module = ast.parse(contract_path.read_text(encoding="utf-8"))

    public_defs = [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]
    assert public_defs == ["main"]

    action_assignments: list[str] = []
    for node in module.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        else:
            names = []

        action_assignments.extend(
            name for name in names if not name.startswith("_") and "action" in name.casefold()
        )
    assert action_assignments == ["ALLOWED_ACTIONS"]


def test_runtime_scripts_are_phase1_shell_wrappers() -> None:
    build_script = _read_text("build-runtime.bat")
    check_script = _read_text("check-runtime.bat")

    assert '..\\tools\\build-runtimes.bat" --module "08 - Semantic Control Kernel"' in build_script
    assert "semantic_control_kernel.bootstrap.runtime_report" in check_script
    assert '"error":{"code":"runtime_missing"' in check_script


def test_phase0_write_scope_has_no_legacy_kernel_folder_names() -> None:
    forbidden_names = (
        "08 - Semantic " + "Release Kernel",
        "Semantic " + "Release Kernel",
    )
    allowed_build_spec_line = "    `" + forbidden_names[0] + "` and `" + forbidden_names[1] + "`."
    violations: list[str] = []

    for scope_entry in PHASE_WRITE_SCOPE:
        path = MODULE_ROOT / scope_entry
        if path.is_dir():
            candidates = [candidate for candidate in path.rglob("*") if candidate.is_file()]
        else:
            candidates = [path]

        for candidate in candidates:
            relative = candidate.relative_to(MODULE_ROOT).as_posix()
            if relative.startswith(("runtime/python/", "dev-tests/.venv/")):
                continue
            if "__pycache__" in candidate.parts or candidate.suffix.lower() in {".pyc", ".pyo", ".exe", ".dll"}:
                continue
            text = candidate.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if (
                    relative == "SPEC_Semantic_Control_Kernel_Build.md"
                    and line == allowed_build_spec_line
                ):
                    continue
                for forbidden_name in forbidden_names:
                    if forbidden_name in line:
                        violations.append(f"{relative}:{line_number}: {forbidden_name}")

    assert violations == []
