from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from semantic_control_kernel import orchestrator_contract
from phase1_contract_support import MODULE_ROOT, load_json


def test_unknown_action_writes_exact_fail_closed_response(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps({"action": "future_workflow", "request_id": "req-001", "payload": {}}),
        encoding="utf-8",
    )

    exit_code = orchestrator_contract.main(["--request", str(request_path), "--response", str(response_path)])

    assert exit_code == 0
    assert load_json(response_path) == {
        "status": "error",
        "request_id": "req-001",
        "error": {
            "code": "unknown_action",
            "message": "Unknown Semantic Control Kernel action: future_workflow",
            "action": "future_workflow",
            "allowed_actions": [],
        },
    }


def test_module_subprocess_unknown_action_writes_fail_closed_response(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps({"action": "future_workflow", "request_id": "req-subprocess", "payload": {}}),
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": str(MODULE_ROOT)}

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "semantic_control_kernel.orchestrator_contract",
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=MODULE_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert load_json(response_path) == {
        "status": "error",
        "request_id": "req-subprocess",
        "error": {
            "code": "unknown_action",
            "message": "Unknown Semantic Control Kernel action: future_workflow",
            "action": "future_workflow",
            "allowed_actions": [],
        },
    }


def test_malformed_json_fails_nonzero_and_writes_structured_response(tmp_path: Path) -> None:
    request_path = tmp_path / "bad-request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text("{", encoding="utf-8")

    exit_code = orchestrator_contract.main(["--request", str(request_path), "--response", str(response_path)])

    assert exit_code != 0
    payload = load_json(response_path)
    assert payload["status"] == "error"
    assert payload["request_id"] is None
    assert payload["error"]["code"] == "invalid_request"


def test_missing_request_file_fails_nonzero_and_writes_structured_response(tmp_path: Path) -> None:
    request_path = tmp_path / "missing.json"
    response_path = tmp_path / "response.json"

    exit_code = orchestrator_contract.main(["--request", str(request_path), "--response", str(response_path)])

    assert exit_code != 0
    payload = load_json(response_path)
    assert payload["status"] == "error"
    assert payload["request_id"] is None
    assert payload["error"]["code"] == "invalid_request"


def test_non_object_payload_fails_nonzero_and_writes_structured_response(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps({"action": "future_workflow", "request_id": "req-002", "payload": []}),
        encoding="utf-8",
    )

    exit_code = orchestrator_contract.main(["--request", str(request_path), "--response", str(response_path)])

    assert exit_code != 0
    payload = load_json(response_path)
    assert payload["status"] == "error"
    assert payload["request_id"] == "req-002"
    assert payload["error"]["code"] == "invalid_request"


def test_invalid_cli_arguments_fail_nonzero_and_write_structured_response(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "future_workflow"}), encoding="utf-8")

    exit_code = orchestrator_contract.main(
        ["--request", str(request_path), "--response", str(response_path), "--response", str(response_path)]
    )

    assert exit_code != 0
    payload = load_json(response_path)
    assert payload["status"] == "error"
    assert payload["request_id"] is None
    assert payload["error"]["code"] == "invalid_request"


def test_unwritable_response_path_fails_nonzero(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response-dir"
    request_path.write_text(json.dumps({"action": "future_workflow"}), encoding="utf-8")
    response_path.mkdir()

    exit_code = orchestrator_contract.main(["--request", str(request_path), "--response", str(response_path)])

    assert exit_code != 0


def test_contract_import_does_not_require_sibling_module_paths() -> None:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(MODULE_ROOT)!r}); "
        "import semantic_control_kernel.orchestrator_contract; "
        "print('ok')"
    )
    env = {**os.environ, "PYTHONPATH": ""}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=MODULE_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "ok"


def test_contract_import_does_not_eagerly_load_later_phase_surfaces() -> None:
    code = (
        "import json, sys; "
        f"sys.path.insert(0, {str(MODULE_ROOT)!r}); "
        "import semantic_control_kernel.orchestrator_contract; "
        "print(json.dumps(sorted(name for name in sys.modules if name.startswith('semantic_control_kernel'))))"
    )
    env = {**os.environ, "PYTHONPATH": ""}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=MODULE_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    imported = set(json.loads(completed.stdout))
    assert "semantic_control_kernel.mcp_contract" not in imported
    assert "semantic_control_kernel.services.agent_tool_invocation_service" not in imported
    assert "semantic_control_kernel.surface.agent_invocation" not in imported
    assert imported <= {
        "semantic_control_kernel",
        "semantic_control_kernel.orchestrator_contract",
        "semantic_control_kernel.orchestrator_contract_background",
        "semantic_control_kernel.orchestrator_contract_cli",
        "semantic_control_kernel.orchestrator_contract_legacy",
    }
