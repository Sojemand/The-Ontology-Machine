from __future__ import annotations

import json
import subprocess

from phase1_runtime_preflight_support import MODULE_ROOT, runtime_env


def test_runtime_report_succeeds_with_built_runtime_and_cleans_state_probe() -> None:
    runtime_python = MODULE_ROOT / "runtime" / "python" / "python.exe"
    assert runtime_python.exists(), "Run build-runtime.bat before the Phase 1 dev suite."

    completed = subprocess.run(
        [
            str(runtime_python),
            "-m",
            "semantic_control_kernel.bootstrap.runtime_report",
            "--root",
            str(MODULE_ROOT),
            "--strict",
        ],
        cwd=MODULE_ROOT,
        env=runtime_env(),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["module_key"] == "semantic_control_kernel"
    assert payload["manifest_status"] == "agent_surface_shell"
    assert payload["contract_version"] == 1
    assert payload["runtime_python"] == str(runtime_python)
    assert {check["name"] for check in payload["checks"]} >= {
        "runtime_python_exists",
        "runtime_stdlib_paths",
        "runtime_has_no_pyvenv_cfg",
        "module_manifest",
        "runtime_manifest",
        "package_import_path",
        "no_sibling_module_sys_path",
        "state_write_probe",
        "working_directory_is_module_root",
        "contract_import_no_side_effects",
    }
    assert not (MODULE_ROOT / "state" / ".runtime_write_probe.tmp").exists()
