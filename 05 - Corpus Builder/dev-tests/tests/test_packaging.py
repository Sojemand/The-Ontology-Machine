from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
ROOT_BUILD_INSTALLER = PIPELINE_ROOT / "tools" / "build-installer.py"
STAGE_ROOT = MODULE_ROOT / "dist" / "stage"


def _run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        check=False,
    )


def _run_batch(script: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run_command(["cmd.exe", "/c", "call", str(script), *arguments], cwd=cwd)


def _stage_bundle() -> Path:
    completed = _run_command(
        [
            sys.executable,
            str(ROOT_BUILD_INSTALLER),
            "--module",
            "05 - Corpus Builder",
            "--skip-runtime-build",
            "--app-version",
            "2099-01-01",
        ],
        cwd=PIPELINE_ROOT,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return STAGE_ROOT


@pytest.fixture(scope="module")
def staged_bundle() -> Path:
    return _stage_bundle()


def test_check_runtime_reports_portable_runtime() -> None:
    completed = _run_batch(MODULE_ROOT / "check-runtime.bat", cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["python"]["path"].lower().endswith("runtime\\python\\python.exe")
    assert payload["provenance"]["sqlite3"].lower().startswith(str((MODULE_ROOT / "runtime" / "python").resolve()).lower())
    assert payload["contract"]["manifest_action_count"] == payload["contract"]["code_action_count"] == 36
    assert payload["contract"]["missing_dispatch_actions"] == []
    assert payload["contract"]["missing_parsers"] == []


def test_installer_stage_excludes_mutable_dirs_and_has_no_run_shortcuts(staged_bundle: Path) -> None:
    stage_root = staged_bundle
    release_manifest = json.loads((stage_root / "release-manifest.json").read_text(encoding="utf-8"))
    iss_script = (MODULE_ROOT / "installer" / "CorpusBuilderVision.iss").read_text(encoding="utf-8")
    assert (stage_root / "runtime" / "runtime-manifest.json").exists()
    assert (stage_root / "check-runtime.bat").exists()
    assert (stage_root / "config" / "search_policy.json").exists()
    assert not (stage_root / "run.bat").exists()
    assert not (stage_root / "state").exists()
    assert not (stage_root / "output").exists()
    assert release_manifest["mutable_dirs"] == ["output", "state"]
    assert release_manifest["excluded_runtime_paths"] == ["runtime\\wheelhouse"]
    assert release_manifest["sign_targets"] == [
        "check-runtime.bat",
        "module-manifest.json",
        "runtime\\runtime-manifest.json",
    ]
    assert "[Icons]" not in iss_script
    assert "desktopicon" not in iss_script
    assert "run.bat" not in iss_script


def test_staged_bundle_runs_without_host_python(staged_bundle: Path) -> None:
    install_root = staged_bundle
    runtime_check = _run_batch(install_root / "check-runtime.bat", cwd=install_root)
    assert runtime_check.returncode == 0, runtime_check.stderr or runtime_check.stdout

    cli_help = _run_command(
        [str(install_root / "runtime" / "python" / "python.exe"), "-m", "corpus_builder", "--help"],
        cwd=install_root,
    )
    assert cli_help.returncode == 0, cli_help.stderr or cli_help.stdout
    assert "Corpus Builder Vision" in cli_help.stdout
