from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _link_or_copy(source: str, destination: str) -> None:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _copy_readonly_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        copy_function=_link_or_copy,
    )


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "validator_module"
    _copy_readonly_tree(PROJECT_ROOT / "validator_vision", module_root / "validator_vision")
    _copy_readonly_tree(PROJECT_ROOT / "config", module_root / "config")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _write_sitecustomize(module_root: Path) -> None:
    (module_root / "sitecustomize.py").write_text(
        """
import json
from pathlib import Path

import validator_vision.orchestrator_contract.workflow as workflow


def _validate_document(command, *args, **kwargs):
    report_path = Path(command.validation_output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"status": "OK"}), encoding="utf-8")
    return {
        "status": "OK",
        "report_path": str(report_path),
        "needs_review": False,
        "detail": "OK (issues=0, fail=0, warn=0)",
        "error": "",
    }


workflow.validate_document = _validate_document
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _invoke_contract(module_root: Path, *, contract_module: str, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = dict(os.environ)
    env["VALIDATOR_VISION_HOME"] = str(module_root / "app_home")
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


def test_standalone_copy_supports_validator_public_contracts(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    _write_sitecustomize(module_root)
    structured_path = tmp_path / "invoice.structured.json"
    structured_path.write_text("{}", encoding="utf-8")
    validation_output_path = tmp_path / "validation" / "invoice.validation_report.json"

    healthcheck = _invoke_contract(
        module_root,
        contract_module="validator_vision.orchestrator_contract",
        payload={"action": "healthcheck"},
    )
    validate = _invoke_contract(
        module_root,
        contract_module="validator_vision.orchestrator_contract",
        payload={
            "action": "validate_document",
            "structured_path": str(structured_path),
            "validation_output_path": str(validation_output_path),
        },
    )

    assert healthcheck["status"] == "ok"
    assert healthcheck["healthy"] is True
    assert healthcheck["dependencies"] == [
        {"name": "config", "kind": "config", "required": True, "healthy": True, "detail": "ok"}
    ]
    assert validate["status"] == "OK"
    assert validation_output_path.exists()


def test_standalone_copy_supports_validator_edit_contract_bundle_actions(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    described = _invoke_contract(
        module_root,
        contract_module="validator_vision.edit_contract",
        payload={"action": "describe_surfaces"},
    )
    bundled = _invoke_contract(
        module_root,
        contract_module="validator_vision.edit_contract",
        payload={"action": "read_bundle"},
    )

    assert described["status"] == "ok"
    assert bundled["status"] == "ok"
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
