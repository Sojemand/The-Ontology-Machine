from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from orchestrator.bootstrap import ModuleRuntimeSpec
from orchestrator.integrations import ModuleContractError, adapter, validation


def _runtime_spec(tmp_path: Path, module_key: str = "interpreter") -> ModuleRuntimeSpec:
    module_root = tmp_path / module_key
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    python_exe = runtime_dir / ("python.exe" if os.name == "nt" else "python")
    python_exe.write_text("", encoding="utf-8")
    manifest_path = module_root / "module-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    return ModuleRuntimeSpec(
        key=module_key,
        display_name="Interpreter",
        module_root=module_root,
        contract_module="demo.contract",
        runtime_dir=runtime_dir,
        python_executable=python_exe,
        manifest_path=manifest_path,
        actions=("interpret_document", "healthcheck"),
    )


def test_invoke_contract_uses_bundled_runtime_and_response_file(tmp_path, monkeypatch) -> None:
    spec = _runtime_spec(tmp_path)

    def fake_run(command, **kwargs):  # noqa: ANN001
        request_path = Path(command[command.index("--request") + 1])
        response_path = Path(command[command.index("--response") + 1])
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert command[:3] == [str(spec.python_executable), "-m", "demo.contract"]
        assert kwargs["cwd"] == spec.module_root
        assert kwargs["timeout"] == 123
        assert payload["action"] == "interpret_document"
        assert payload["request_path"] == "doc.request.json"
        response_path.write_text(json.dumps({"status": "ok", "structured_path": "out.json"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("orchestrator.integrations.adapter.subprocess.run", fake_run)

    result = adapter.invoke_contract(
        spec,
        {"action": "interpret_document", "request_path": "doc.request.json", "structured_output_path": "out.json"},
        timeout=123,
    )

    assert result["status"] == "ok"
    assert result["structured_path"] == "out.json"


def test_invoke_contract_passes_ephemeral_env_overlay_without_writing_secret_into_request(tmp_path, monkeypatch) -> None:
    spec = _runtime_spec(tmp_path)

    def fake_run(command, **kwargs):  # noqa: ANN001
        request_path = Path(command[command.index("--request") + 1])
        response_path = Path(command[command.index("--response") + 1])
        request_text = request_path.read_text(encoding="utf-8")
        assert "super-secret" not in request_text
        assert kwargs["env"]["VISION_OPENAI_AUTH_MODE"] == "api_keys"
        assert kwargs["env"]["VISION_OPENAI_API_KEY"] == "super-secret"
        response_path.write_text(json.dumps({"status": "ok", "structured_path": "out.json"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("orchestrator.integrations.adapter.subprocess.run", fake_run)

    result = adapter.invoke_contract(
        spec,
        {"action": "interpret_document", "request_path": "doc.request.json", "structured_output_path": "out.json"},
        timeout=123,
        env_overlay={"VISION_OPENAI_AUTH_MODE": "api_keys", "VISION_OPENAI_API_KEY": "super-secret"},
    )

    assert result["status"] == "ok"


def test_launch_contract_process_uses_persistent_paths_and_overlay(tmp_path, monkeypatch) -> None:
    spec = _runtime_spec(tmp_path)
    request_path = tmp_path / "session" / "request.json"
    response_path = tmp_path / "session" / "response.json"
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text("stale", encoding="utf-8")
    captured: dict[str, object] = {}
    process = object()

    def fake_popen(command, **kwargs):  # noqa: ANN001
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        captured["payload"] = json.loads(request_path.read_text(encoding="utf-8"))
        assert not response_path.exists()
        return process

    monkeypatch.setattr("orchestrator.integrations.adapter.subprocess.Popen", fake_popen)

    launched = adapter.launch_contract_process(
        spec,
        {"action": "interpret_document", "request_path": "doc.request.json"},
        request_path=request_path,
        response_path=response_path,
        env_overlay={"VISION_OPENAI_AUTH_MODE": "api_keys"},
    )

    assert launched is process
    assert captured["command"][:3] == [str(spec.python_executable), "-m", "demo.contract"]
    assert captured["cwd"] == spec.module_root
    assert captured["payload"] == {"action": "interpret_document", "request_path": "doc.request.json"}
    assert captured["env"]["VISION_OPENAI_AUTH_MODE"] == "api_keys"


def test_invoke_contract_requires_bundled_runtime(tmp_path) -> None:
    module_root = tmp_path / "interpreter"
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = module_root / "module-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    spec = ModuleRuntimeSpec(
        key="interpreter",
        display_name="Interpreter",
        module_root=module_root,
        contract_module="demo.contract",
        runtime_dir=runtime_dir,
        python_executable=runtime_dir / "python.exe",
        manifest_path=manifest_path,
    )

    with pytest.raises(FileNotFoundError, match="Bundled runtime is missing"):
        adapter.invoke_contract(spec, {"action": "interpret_document"}, timeout=10)


def test_invoke_contract_raises_contract_error_on_nonzero_exit(tmp_path, monkeypatch) -> None:
    spec = _runtime_spec(tmp_path)

    def fake_run(command, **kwargs):  # noqa: ANN001
        response_path = Path(command[command.index("--response") + 1])
        response_path.write_text(json.dumps({"error": "contract exploded"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="boom")

    monkeypatch.setattr("orchestrator.integrations.adapter.subprocess.run", fake_run)

    with pytest.raises(ModuleContractError, match="Interpreter failed: contract exploded"):
        adapter.invoke_contract(spec, {"action": "interpret_document"}, timeout=10)


def test_load_contract_response_rejects_non_object_root(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    response_path.write_text('["bad"]', encoding="utf-8")

    with pytest.raises(ModuleContractError, match="Response file is not a JSON object"):
        validation.load_contract_response(response_path)


def test_load_contract_response_returns_empty_dict_for_missing_file(tmp_path: Path) -> None:
    assert validation.load_contract_response(tmp_path / "missing.json") == {}
