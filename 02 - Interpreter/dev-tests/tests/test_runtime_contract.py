from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


def _module_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _package_root() -> Path:
    return _module_root() / "llm_interpreter"


def _assert_package_files_stay_under_200_loc(package_root: Path) -> None:
    for file_path in package_root.rglob("*.py"):
        relative = file_path.relative_to(package_root)
        if "__pycache__" in relative.parts:
            continue
        assert len(file_path.read_text(encoding="utf-8").splitlines()) <= 200, relative


def _assert_python_files_do_not_exceed_depth(package_root: Path, *, max_depth: int) -> None:
    for file_path in package_root.rglob("*.py"):
        relative = file_path.relative_to(package_root)
        if "__pycache__" in relative.parts:
            continue
        assert len(relative.parts) <= max_depth, relative


_TEST_LOC_EXCEPTIONS: dict[Path, str] = {}


def _assert_test_loc_exceptions_are_explicit(tests_root: Path) -> None:
    seen: set[Path] = set()
    for file_path in tests_root.rglob("*.py"):
        relative = file_path.relative_to(tests_root)
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        if line_count <= 200:
            continue
        assert relative in _TEST_LOC_EXCEPTIONS, f"{relative} has {line_count} LOC without governance exception"
        seen.add(relative)
    assert seen == set(_TEST_LOC_EXCEPTIONS)


def test_manifest_and_scripts_point_to_interpreter_module() -> None:
    module_root = _module_root()
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    build_runtime_wrapper = (module_root / "tools" / "build-runtime.bat").read_text(encoding="utf-8")
    build_runtime = (module_root / "tools" / "build-runtime.ps1").read_text(encoding="utf-8")
    build_installer = (module_root / "build-installer.bat").read_text(encoding="utf-8")

    assert manifest["module_key"] == "interpreter"
    assert manifest["launcher_module"] == "llm_interpreter"
    assert manifest["contract_module"] == "llm_interpreter.orchestrator_contract"
    assert manifest["actions"] == ["interpret_document", "healthcheck", "debug_run", "generate_llm"]
    assert not (module_root / "build-runtime.bat").exists()
    assert "build-runtime.ps1" in build_runtime_wrapper
    assert "build-runtimes.bat" in build_runtime
    assert '"02 - Interpreter"' in build_runtime
    assert 'tools\\build-installer.py' in build_installer
    assert '--module "02 - Interpreter"' in build_installer


def test_public_surfaces_use_flat_package_layout() -> None:
    package_root = _package_root()

    assert (package_root / "config_bootstrap.py").exists()
    assert (package_root / "orchestrator_contract" / "__init__.py").exists()
    assert (package_root / "orchestrator_contract" / "__main__.py").exists()
    assert (package_root / "edit_contract" / "__main__.py").exists()
    assert (package_root / "edit_contract" / "describe_surfaces.py").exists()
    assert (package_root / "runtime_support.py").exists()
    assert (package_root / "providers" / "openai_surface.py").exists()
    assert (package_root / "providers" / "openai_payload.py").exists()
    assert not (package_root / "prompts" / "prompt_view.py").exists()
    assert (package_root / "orchestrator_contract" / "debug_processing.py").exists()
    assert not (package_root / "providers" / "openai_provider").exists()
    assert not (package_root.parent / "llm_interpreter_file").exists()
    assert not (package_root / "main").exists()
    assert not (package_root / "ui").exists()
    assert not (_module_root() / "run.bat").exists()
    assert not (package_root.parent / "__main__.py").exists()


def test_package_python_files_stay_under_200_loc() -> None:
    _assert_package_files_stay_under_200_loc(_package_root())
    _assert_python_files_do_not_exceed_depth(_package_root(), max_depth=2)


def test_test_loc_exceptions_are_visible() -> None:
    _assert_test_loc_exceptions_are_explicit(_module_root() / "dev-tests" / "tests")


def test_readme_documents_runtime_debug_and_packaging_contract() -> None:
    readme = (_module_root() / "README.md").read_text(encoding="utf-8").lower()

    assert "%localappdata%\\enterprise stack\\interpreter" in readme
    assert "interpreter_home" in readme
    assert ".appdata" in readme
    assert "config\\prompt_bundle" in readme
    assert "interpreter.runtime_policy_env" in readme
    assert "interpreter.execution_limits" in readme
    assert "tools\\build-runtime.bat" in readme
    assert "check-runtime.bat" in readme
    assert "installer.bat" in readme
    assert "build-installer.bat" in readme


def test_runtime_docs_and_manifests_track_portable_runtime_surface() -> None:
    module_root = _module_root()
    runtime_readme = (module_root / "runtime" / "README.md").read_text(encoding="utf-8").lower()
    runtime_manifest = json.loads((module_root / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    installer_manifest = json.loads((module_root / "installer" / "installer-manifest.json").read_text(encoding="utf-8"))

    assert "runtime/runtime-manifest.json" in runtime_readme
    assert "tools/build-runtime.bat" in runtime_readme
    assert "runtime/requirements.lock.txt" in runtime_manifest["required_files"]
    assert "llm_interpreter/config_bootstrap.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/orchestrator_contract/__main__.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/orchestrator_contract/generate_action.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/edit_contract/__main__.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/edit_contract/describe_surfaces.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/orchestrator_contract/debug_support.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/runtime_paths.py" in runtime_manifest["required_files"]
    assert "llm_interpreter/runtime_support.py" in runtime_manifest["required_files"]
    assert "run.bat" not in runtime_manifest["required_files"]
    assert "build-runtime.bat" not in runtime_manifest["required_files"]
    assert installer_manifest["script_name"] == "Interpreter.iss"
    assert installer_manifest["mutable_dirs"] == ["config", "state", "output", "logs", ".appdata"]
    assert "runtime\\runtime-manifest.json" in installer_manifest["sign_targets"]
    assert "tools\\installer.ps1" in installer_manifest["sign_targets"]
    assert "build-installer.bat" not in installer_manifest["sign_targets"]
    assert "run.bat" not in installer_manifest["sign_targets"]


def test_import_audit_allows_only_stdlib_and_local() -> None:
    allowed_roots = set(sys.stdlib_module_names) | {"__future__", "llm_interpreter"}

    for file_path in _package_root().rglob("*.py"):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root in allowed_roots, f"{file_path}: unerlaubter Import {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    continue
                module = node.module or ""
                root = module.split(".")[0]
                assert root in allowed_roots, f"{file_path}: unerlaubter Import {module}"
