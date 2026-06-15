from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "interpreter_module"
    shutil.copytree(PROJECT_ROOT / "llm_interpreter", module_root / "llm_interpreter")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _write_sitecustomize(module_root: Path) -> None:
    (module_root / "sitecustomize.py").write_text(
        """
import json
from pathlib import Path

import llm_interpreter.orchestrator_contract.workflow as workflow


def _healthcheck(*args, **kwargs):
    return {"status": "ok", "healthy": True, "message": "", "dependencies": []}


def _interpret_document(payload, *args, **kwargs):
    output_path = Path(str(payload["structured_output_path"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"document_type": "invoice", "source": {"request_path": payload["request_path"]}}, indent=2), encoding="utf-8")
    return {"status": "ok", "structured_output_path": str(output_path), "needs_review": False, "review_reason": ""}


workflow.healthcheck = _healthcheck
workflow.interpret_document = _interpret_document
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _invoke_contract(module_root: Path, *, contract_module: str, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = dict(os.environ)
    env["INTERPRETER_HOME"] = str(module_root / "app_home")
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


def test_standalone_copy_supports_interpreter_public_contracts(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    _write_sitecustomize(module_root)
    interpreter_request = tmp_path / "invoice.request.json"
    interpreter_request.write_text(json.dumps({"source": {"path": "invoice.pdf"}}), encoding="utf-8")
    structured_output_path = tmp_path / "structured" / "invoice.structured.json"
    file_output_path = tmp_path / "structured" / "invoice.file.structured.json"

    healthcheck = _invoke_contract(
        module_root,
        contract_module="llm_interpreter.orchestrator_contract",
        payload={"action": "healthcheck", "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 8000}},
    )
    interpret = _invoke_contract(
        module_root,
        contract_module="llm_interpreter.orchestrator_contract",
        payload={
            "action": "interpret_document",
            "request_path": str(interpreter_request),
            "structured_output_path": str(structured_output_path),
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 8000},
        },
    )
    file_interpret = _invoke_contract(
        module_root,
        contract_module="llm_interpreter.orchestrator_contract",
        payload={
            "action": "interpret_document",
            "interpreter_profile": "file",
            "request_path": str(interpreter_request),
            "structured_output_path": str(file_output_path),
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 8000},
        },
    )

    assert healthcheck["status"] == "ok"
    assert healthcheck["healthy"] is True
    assert interpret["status"] == "ok"
    assert file_interpret["status"] == "ok"
    assert structured_output_path.exists()
    assert file_output_path.exists()


def test_standalone_copy_supports_interpreter_edit_contract_bundle_actions(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    described = _invoke_contract(
        module_root,
        contract_module="llm_interpreter.edit_contract",
        payload={"action": "describe_surfaces"},
    )
    bundled = _invoke_contract(
        module_root,
        contract_module="llm_interpreter.edit_contract",
        payload={"action": "read_bundle"},
    )

    assert described["status"] == "ok"
    assert bundled["status"] == "ok"
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
