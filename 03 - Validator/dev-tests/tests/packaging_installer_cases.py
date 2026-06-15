from __future__ import annotations

import json
import os

from packaging_support import (
    BUILD_INSTALLER,
    BUILD_RUNTIME_PS1,
    INSTALLER,
    INSTALLER_ISS,
    MODULE_ROOT,
    RUNTIME_ROOT,
    TEST_DATA,
    _run_batch,
    _run_command,
    _stage_bundle,
)


def test_build_installer_wrapper_targets_validator_module() -> None:
    script = BUILD_INSTALLER.read_text(encoding="utf-8")
    assert '--module "03 - Validator"' in script


def test_build_runtime_rejects_incomplete_source_before_touching_existing_runtime(scratch_dir) -> None:
    bad_source = scratch_dir / "bad-runtime"
    bad_source.mkdir()

    completed = _run_command(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(BUILD_RUNTIME_PS1),
            "-SourceRuntime",
            str(bad_source),
        ],
        cwd=MODULE_ROOT,
    )

    combined = completed.stderr or completed.stdout
    assert completed.returncode != 0
    assert "Portable Python-Quelle ist unvollstaendig" in combined
    assert (RUNTIME_ROOT / "python.exe").exists()
    assert (RUNTIME_ROOT / "Lib" / "encodings" / "__init__.py").exists()


def test_build_runtime_uses_staged_swap_with_backup() -> None:
    script = BUILD_RUNTIME_PS1.read_text(encoding="utf-8")
    assert "Move-StagedRuntimeIntoPlace" in script
    assert ".python-stage-" in script
    assert ".python-backup-" in script
    assert "Runtime-Check nach Staging-Swap fehlgeschlagen" in script


def test_installer_seeds_user_config_atomically() -> None:
    script = (MODULE_ROOT / "tools" / "installer.ps1").read_text(encoding="utf-8")
    assert "function Copy-FileAtomic" in script
    assert "Copy-FileAtomic -SourcePath $bundledConfig -TargetPath $userConfig" in script


def test_installer_publishes_app_from_checked_stage() -> None:
    script = (MODULE_ROOT / "tools" / "installer.ps1").read_text(encoding="utf-8")
    assert "function New-InstallStage" in script
    assert "function Publish-StagedInstall" in script
    assert ".app-stage-" in script
    assert ".app-backup-" in script
    assert "Invoke-RuntimeCheck -RootDir $script:InstallRoot" in script


def test_inno_setup_script_tracks_validator_packaging_contract() -> None:
    script = INSTALLER_ISS.read_text(encoding="utf-8")
    assert "OutputBaseFilename=ValidatorVision-Setup-{#AppVersion}" in script
    assert "DefaultDirName={#MyAppHome}\\app" in script
    assert 'Source: "{#SourceDir}\\config\\config.json"; DestDir: "{#MyAppHome}\\config"' in script
    assert "uninsneveruninstall" in script


def test_installer_stage_excludes_mutable_dirs_and_tracks_sign_targets() -> None:
    stage_root = _stage_bundle()
    release_manifest = json.loads((stage_root / "release-manifest.json").read_text(encoding="utf-8"))
    assert (stage_root / "runtime" / "runtime-manifest.json").exists()
    assert (stage_root / "check-runtime.bat").exists()
    assert not (stage_root / "state").exists()
    assert not (stage_root / "output").exists()
    assert not (stage_root / "run.bat").exists()
    assert release_manifest["mutable_dirs"] == ["output", "state"]
    assert release_manifest["excluded_runtime_paths"] == ["runtime\\wheelhouse"]
    assert release_manifest["sign_targets"] == [
        "check-runtime.bat",
        "module-manifest.json",
        "runtime\\runtime-manifest.json",
    ]


def test_installer_requires_localappdata_without_install_root(scratch_dir) -> None:
    env = os.environ.copy()
    env.pop("LOCALAPPDATA", None)
    completed = _run_batch(INSTALLER, "-CheckOnly", cwd=MODULE_ROOT, env=env)
    assert completed.returncode != 0
    assert "LOCALAPPDATA ist nicht gesetzt" in (completed.stderr or completed.stdout)


def test_installer_creates_contract_only_portable_install(scratch_dir) -> None:
    app_home = scratch_dir / "portable-install"
    install_root = app_home / "app"
    install = _run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert install.returncode == 0, install.stderr or install.stdout
    assert (install_root / "runtime" / "runtime-manifest.json").exists()
    assert not (install_root / "run.bat").exists()
    assert (app_home / "config" / "config.json").exists()

    installed_check = _run_batch(install_root / "check-runtime.bat", cwd=install_root)
    assert installed_check.returncode == 0, installed_check.stderr or installed_check.stdout

    env = os.environ.copy()
    env["VALIDATOR_VISION_HOME"] = str(app_home)
    report_path = app_home / "reports" / "invoice_ok.vision_validation_report.json"
    validate = _run_command(
        [
            str(install_root / "runtime" / "python" / "python.exe"),
            "-m",
            "validator_vision",
            "validate",
            "--structured",
            str(TEST_DATA / "invoice_ok.structured.json"),
            "--report",
            str(report_path),
        ],
        cwd=install_root,
        env=env,
    )
    assert validate.returncode == 0, validate.stderr or validate.stdout
    assert report_path.exists()
