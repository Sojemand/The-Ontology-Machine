from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "optimizer_module"
    shutil.copytree(PROJECT_ROOT / "optimizer_ocr", module_root / "optimizer_ocr")
    shutil.copytree(PROJECT_ROOT / "ingestion_layer_vision", module_root / "ingestion_layer_vision")
    shutil.copytree(PROJECT_ROOT / "ingestion_layer_file", module_root / "ingestion_layer_file")
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _write_sitecustomize(module_root: Path) -> None:
    (module_root / "sitecustomize.py").write_text(
        """
import json
from pathlib import Path

import ingestion_layer_vision.orchestrator_contract.workflow as workflow


def _healthcheck(*args, **kwargs):
    return {"status": "ok", "healthy": True, "message": "", "dependencies": []}


def _scan_debug_input(payload, *args, **kwargs):
    session_root = Path(str(payload["session_root"]))
    report_path = session_root / "outputs" / "preview_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"status": "ok"}), encoding="utf-8")
    return {"status": "ok", "summary": "scan complete", "outputs": {"preview_report": str(report_path)}}


workflow.healthcheck = _healthcheck
workflow.scan_debug_input = _scan_debug_input
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _invoke_contract(module_root: Path, *, contract_module: str, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = dict(os.environ)
    env["OPTIMIZER_HOME"] = str(module_root / "app_home")
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


def test_standalone_copy_supports_optimizer_public_contracts(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    _write_sitecustomize(module_root)
    input_root = tmp_path / "pipeline"
    input_root.mkdir(parents=True, exist_ok=True)

    healthcheck = _invoke_contract(
        module_root,
        contract_module="ingestion_layer_vision.orchestrator_contract",
        payload={"action": "healthcheck"},
    )
    scan = _invoke_contract(
        module_root,
        contract_module="ingestion_layer_vision.orchestrator_contract",
        payload={
            "action": "scan_debug_input",
            "mode": "scan",
            "session_root": str(tmp_path / "scan-session"),
            "input_root": str(input_root),
        },
    )

    assert healthcheck["status"] == "ok"
    assert healthcheck["healthy"] is True
    assert scan["status"] == "ok"
    assert (tmp_path / "scan-session" / "outputs" / "preview_report.json").exists()


def test_standalone_copy_supports_optimizer_edit_contract_bundle_actions(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    described = _invoke_contract(
        module_root,
        contract_module="ingestion_layer_vision.edit_contract",
        payload={"action": "describe_surfaces"},
    )
    bundled = _invoke_contract(
        module_root,
        contract_module="ingestion_layer_vision.edit_contract",
        payload={"action": "read_bundle"},
    )

    assert described["status"] == "ok"
    assert bundled["status"] == "ok"
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
