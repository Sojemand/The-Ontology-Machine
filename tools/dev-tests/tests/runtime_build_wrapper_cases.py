from __future__ import annotations

from runtime_build_tooling_support import (
    CLIENT_FRONTEND_BUILD_SCRIPT_PATH,
    INTERPRETER_BUILD_HOOK_PATH,
    INTERPRETER_BUILD_PS1_PATH,
    INTERPRETER_BUILD_SCRIPT_PATH,
    INTERPRETER_REQUIREMENTS_PATH,
    OPTIMIZER_BUILD_PS1_PATH,
    OPTIMIZER_BUILD_SCRIPT_PATH,
    OPTIMIZER_REQUIREMENTS_PATH,
    load_tool_module,
)


def test_optimizer_build_runtime_wrapper_uses_pipeline_builder() -> None:
    script = OPTIMIZER_BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
    powershell = OPTIMIZER_BUILD_PS1_PATH.read_text(encoding="utf-8")

    assert "build-runtime.ps1" in script
    assert "build-runtimes.bat" in powershell
    assert '"01 - Optimizer"' in powershell
    assert "--archive-wheelhouse" in powershell


def test_interpreter_build_runtime_wrapper_uses_pipeline_builder() -> None:
    script = INTERPRETER_BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
    powershell = INTERPRETER_BUILD_PS1_PATH.read_text(encoding="utf-8")

    assert "build-runtime.ps1" in script
    assert "build-runtimes.bat" in powershell
    assert '"02 - Interpreter"' in powershell
    assert "--archive-wheelhouse" in powershell


def test_client_frontend_build_runtime_wrapper_uses_pipeline_builder() -> None:
    script = CLIENT_FRONTEND_BUILD_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "build-runtimes.bat" in script
    assert '--module "Client Frontend"' in script
    assert "--offline" in script


def test_optimizer_runtime_requirements_cover_merged_profiles() -> None:
    lines = {
        line.strip()
        for line in OPTIMIZER_REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert {
        "pyyaml>=6.0.0",
        "pdfplumber>=0.11.0",
        "PyMuPDF>=1.24.0",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "python-docx>=1.1.0",
    }.issubset(lines)


def test_interpreter_runtime_requirements_stay_headless() -> None:
    lines = [line.strip() for line in INTERPRETER_REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert lines == ["# Headless runtime: no third-party Python dependencies."]


def test_interpreter_runtime_manifest_hook_tracks_headless_surface() -> None:
    module = load_tool_module("test_build_runtimes_interpreter_hook", INTERPRETER_BUILD_HOOK_PATH)

    payload = module._runtime_manifest_payload("llm_interpreter")

    assert payload["python_version"] == "3.11"
    assert "llm_interpreter/orchestrator_contract/__main__.py" in payload["required_files"]
    assert "llm_interpreter/orchestrator_contract/debug_support.py" in payload["required_files"]
    assert "llm_interpreter/runtime_paths.py" in payload["required_files"]
    assert "run.bat" not in payload["required_files"]
    assert "runtime/python/Lib/tkinter/__init__.py" not in payload["required_files"]


def test_interpreter_runtime_manifest_hook_prunes_gui_runtime_bits(tmp_path) -> None:
    module = load_tool_module("test_build_runtimes_interpreter_prune", INTERPRETER_BUILD_HOOK_PATH)
    runtime_dir = tmp_path / "runtime" / "python"
    runtime_dir.mkdir(parents=True)

    for relative_path in module.HEADLESS_RUNTIME_PATHS:
        target = runtime_dir / relative_path
        if relative_path.suffix:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("stub", encoding="utf-8")
        else:
            target.mkdir(parents=True, exist_ok=True)

    module._finalize_runtime_layout(runtime_dir)

    for relative_path in module.HEADLESS_RUNTIME_PATHS:
        assert not (runtime_dir / relative_path).exists()
