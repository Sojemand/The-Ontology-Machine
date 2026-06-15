from __future__ import annotations

from pathlib import Path

from runtime_build_tooling_support import OPTIMIZER_ROOT, TOOLS_ROOT, VALIDATOR_ROOT, load_tool_module


def test_runtime_validation_modules_cover_optimizer_runtime_imports() -> None:
    module = load_tool_module("test_build_runtimes_optimizer", TOOLS_ROOT / "build-runtimes.py")

    target = module.ModuleBuildTarget(OPTIMIZER_ROOT)
    modules = module._runtime_validation_modules(target)

    assert "pdfminer" in modules
    assert "pdfplumber" in modules
    assert "fitz" in modules
    assert "yaml" in modules
    assert "PIL" in modules
    assert "numpy" in modules
    assert "extract_msg" in modules
    assert "docx" in modules
    assert "odf" in modules
    assert "striprtf" in modules
    assert "bs4" in modules
    assert "olefile" in modules
    assert "oletools" in modules
    assert "RTFDE" in modules


def test_optimizer_target_tracks_active_plugin_bootstraps_and_bundled_libreoffice() -> None:
    module = load_tool_module("test_build_runtimes_optimizer_plugins", TOOLS_ROOT / "build-runtimes.py")

    target = module.ModuleBuildTarget(OPTIMIZER_ROOT)

    assert target.bundles_libreoffice is True
    assert target.plugin_bootstraps == (OPTIMIZER_ROOT / "plugins" / "mail-outlook-store" / "bootstrap.py",)


def test_package_name_prefers_launcher_module_when_present() -> None:
    module = load_tool_module("test_build_runtimes_validator", TOOLS_ROOT / "build-runtimes.py")

    target = module.ModuleBuildTarget(VALIDATOR_ROOT)

    assert target.package_name == "validator_vision"


def test_build_bundled_libreoffice_runtime_copies_and_validates(monkeypatch, tmp_path) -> None:
    module = load_tool_module("test_build_runtimes_libreoffice", TOOLS_ROOT / "build-runtimes.py")

    target_root = tmp_path / "01 - Optimizer"
    source_root = tmp_path / "LibreOffice"
    (source_root / "program").mkdir(parents=True)
    (source_root / "program" / "soffice.exe").write_text("stub", encoding="utf-8")
    target = module.ModuleBuildTarget(target_root)
    recorded: dict[str, object] = {}

    monkeypatch.setattr(module, "_resolve_libreoffice_source_root", lambda: source_root)

    def fake_run(command, *, cwd, env=None, capture_output=False):
        recorded["command"] = command
        recorded["cwd"] = cwd
        recorded["capture_output"] = capture_output
        return None

    monkeypatch.setattr(module, "_run", fake_run)

    module._build_bundled_libreoffice_runtime(target, clean=True, validate_only=False)

    assert target.libreoffice_soffice.exists()
    assert recorded["cwd"] == target_root
    assert recorded["capture_output"] is True
    assert recorded["command"] == [str(target.libreoffice_soffice), "--version"]


def test_orchestrator_runtime_sanity_check_imports_current_package(monkeypatch, tmp_path) -> None:
    module = load_tool_module("test_build_runtimes_orchestrator", TOOLS_ROOT / "build-runtimes.py")

    target_root = tmp_path / "00 - Orchestrator"
    runtime_dir = target_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True)
    target = module.ModuleBuildTarget(target_root)
    recorded: dict[str, object] = {}

    monkeypatch.setattr(module, "runtime_python", lambda _runtime_dir: Path("python"))
    monkeypatch.setattr(module, "_portable_runtime_env", lambda _runtime_dir: {"PYTHONHOME": str(_runtime_dir)})

    def fake_run(command, *, cwd, env=None, capture_output=False):
        recorded["command"] = command
        recorded["cwd"] = cwd
        recorded["env"] = env
        recorded["capture_output"] = capture_output
        return None

    monkeypatch.setattr(module, "_run", fake_run)

    module._sanity_check_orchestrator_runtime(target)

    assert recorded["cwd"] == target_root
    assert recorded["env"] == {"PYTHONHOME": str(runtime_dir)}
    assert recorded["capture_output"] is False
    assert recorded["command"][:2] == ["python", "-c"]
    assert recorded["command"][2].startswith(
        "import importlib.metadata as metadata; "
        "import customtkinter; "
        "import tkinter; "
        "import orchestrator; "
    )
