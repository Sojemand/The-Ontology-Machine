from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _copy_module(tmp_path: Path) -> Path:
    pipeline_root = tmp_path / "pipeline"
    module_root = pipeline_root / "06 - Edit Suite"
    module_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PROJECT_ROOT / "edit_suite", module_root / "edit_suite")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _invoke_contract(module_root: Path, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "edit_suite.orchestrator_contract",
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=module_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))


def test_standalone_copy_supports_edit_suite_healthcheck(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    healthcheck = _invoke_contract(module_root, {"action": "healthcheck"})

    assert healthcheck["status"] == "ok"
    assert healthcheck["healthy"] is True
    assert healthcheck["module_count"] >= 0
