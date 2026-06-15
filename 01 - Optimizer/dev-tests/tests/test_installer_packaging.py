from __future__ import annotations

import json
import shutil

from packaging_contract_support import BUILD_INSTALLER, DIST_ROOT, INSTALLER, MODULE_ROOT, STAGE_ROOT, run_batch


def test_inno_setup_does_not_define_app_shortcuts():
    script = (MODULE_ROOT / "installer" / "Optimizer.iss").read_text(encoding="utf-8")
    assert "[Icons]" not in script
    assert "run.bat" not in script
    assert "desktopicon" not in script


def test_installer_check_only_validates_runtime_without_local_ocr_probe():
    completed = run_batch(INSTALLER, "-CheckOnly", cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["runtime"]["ok"] is True
    assert set(payload) == {"ok", "source_root", "runtime"}


def test_installer_creates_portable_install_and_preserves_mutable_state(scratch_dir):
    app_home = scratch_dir / "portable-install"
    install_root = app_home / "app"
    install = run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert install.returncode == 0, install.stderr or install.stdout
    payload = json.loads(install.stdout)
    assert payload["ok"] is True
    assert {"ok", "source_root", "install_root", "app_home", "runtime"} == set(payload)
    assert (install_root / "runtime" / "runtime-manifest.json").exists()
    assert (install_root / "ingestion_layer_vision" / "orchestrator_contract" / "__init__.py").exists()
    assert (install_root / "ingestion_layer_file" / "orchestrator_contract" / "__init__.py").exists()
    assert (app_home / "config" / "config.yaml").exists()
    assert not any(path.name.startswith("ocr-") for path in (install_root / "plugins").iterdir())
    keep_state = app_home / "state" / "keep.txt"
    keep_state.write_text("persist", encoding="utf-8")
    reinstall = run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert reinstall.returncode == 0, reinstall.stderr or reinstall.stdout
    assert keep_state.read_text(encoding="utf-8") == "persist"
    installed_check = run_batch(install_root / "check-runtime.bat", cwd=install_root)
    assert installed_check.returncode == 0, installed_check.stderr or installed_check.stdout
    installed_payload = json.loads(installed_check.stdout)
    assert installed_payload["ok"] is True
    assert installed_payload["provenance"]["optimizer_file_contract"].lower().startswith(str(install_root).lower())
    assert not (install_root / "run.bat").exists()

def test_build_installer_stage_uses_portable_contracts():
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    try:
        stage = run_batch(BUILD_INSTALLER, "--skip-runtime-build", cwd=MODULE_ROOT)
        assert stage.returncode == 0, stage.stderr or stage.stdout
        release_manifest = json.loads((STAGE_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        assert release_manifest["mutable_dirs"] == ["output", "state", "logs", ".appdata"]
        assert release_manifest["mutable_files"] == []
        assert release_manifest["excluded_runtime_paths"] == ["runtime\\wheelhouse"]
        assert release_manifest["sign_targets"] == [
            "check-runtime.bat",
            "installer.bat",
            "module-manifest.json",
            "runtime\\runtime-manifest.json",
            "tools\\check-runtime.ps1",
            "tools\\installer.ps1",
        ]
        assert "run.bat" not in release_manifest["sign_targets"]
        assert not any(path.name.startswith("ocr-") for path in (STAGE_ROOT / "plugins").iterdir())
        assert not (STAGE_ROOT / "run.bat").exists()
    finally:
        shutil.rmtree(DIST_ROOT, ignore_errors=True)
