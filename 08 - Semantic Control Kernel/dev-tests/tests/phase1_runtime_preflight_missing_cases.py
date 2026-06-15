from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from phase1_runtime_preflight_support import MODULE_ROOT, fixture_module_root
from semantic_control_kernel.bootstrap import runtime_report


def test_missing_runtime_fixture_returns_runtime_missing(tmp_path: Path) -> None:
    root = fixture_module_root(tmp_path, runtime_python=False)

    report = runtime_report.build_report(root, strict=True, sys_path=[str(root), *os.sys.path], cwd=root)

    assert report["ok"] is False
    assert report["status"] == "error"
    assert report["error"]["code"] == "runtime_missing"


def test_check_runtime_bat_missing_runtime_prints_single_json_error(tmp_path: Path) -> None:
    shutil.copyfile(MODULE_ROOT / "check-runtime.bat", tmp_path / "check-runtime.bat")

    completed = subprocess.run(
        ["cmd.exe", "/c", ".\\check-runtime.bat"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    payload = json.loads(completed.stdout.strip())
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["module_key"] == "semantic_control_kernel"
    assert payload["error"]["code"] == "runtime_missing"
