from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "orchestrator_module"
    shutil.copytree(PROJECT_ROOT / "orchestrator", module_root / "orchestrator")
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    shutil.copy2(PROJECT_ROOT / "module-registry.json", module_root / "module-registry.json")
    return module_root


def _write_sitecustomize(module_root: Path) -> None:
    (module_root / "sitecustomize.py").write_text(
        """
import orchestrator.orchestrator_contract.workflow as workflow


def _healthcheck(*args, **kwargs):
    return {"status": "ok", "healthy": True, "message": "", "dependencies": []}


def _reset_pipeline_logs_action(*args, **kwargs):
    return {"status": "ok", "summary": {"removed_runs": 1, "removed_pipeline_logs": 1}}


workflow.healthcheck = _healthcheck
workflow.reset_pipeline_logs_action = _reset_pipeline_logs_action
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _invoke_contract(module_root: Path, *, contract_module: str, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(module_root) if not existing_pythonpath else os.pathsep.join((str(module_root), existing_pythonpath))
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            contract_module,
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=module_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))


def test_standalone_copy_supports_orchestrator_public_contracts(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    _write_sitecustomize(module_root)

    healthcheck = _invoke_contract(
        module_root,
        contract_module="orchestrator.orchestrator_contract",
        payload={"action": "healthcheck"},
    )
    reset_logs = _invoke_contract(
        module_root,
        contract_module="orchestrator.orchestrator_contract",
        payload={"action": "reset_pipeline_logs", "ui_state": {}},
    )

    assert healthcheck["status"] == "ok"
    assert healthcheck["healthy"] is True
    assert reset_logs["status"] == "ok"
    assert reset_logs["summary"]["removed_pipeline_logs"] == 1


def test_standalone_copy_supports_orchestrator_edit_contract_bundle_actions(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    described = _invoke_contract(
        module_root,
        contract_module="orchestrator.edit_contract",
        payload={"action": "describe_surfaces"},
    )
    bundled = _invoke_contract(
        module_root,
        contract_module="orchestrator.edit_contract",
        payload={"action": "read_bundle"},
    )

    assert described["status"] == "ok"
    assert bundled["status"] == "ok"
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
