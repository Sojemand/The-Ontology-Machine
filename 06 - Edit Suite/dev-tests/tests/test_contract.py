from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import MODULE_ROOT, PIPELINE_ROOT
from edit_suite.contract_runtime import adapter as runtime_adapter
from edit_suite.contract_runtime import invoke_owner_contract


def _run_contract(tmp_path: Path, payload: dict) -> dict:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
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
        cwd=MODULE_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))


def test_contract_healthcheck_returns_ok(tmp_path: Path) -> None:
    payload = _run_contract(tmp_path, {"action": "healthcheck"})
    assert payload["status"] == "ok"
    assert payload["healthy"] is True
    assert payload["module_count"] >= 0


def test_contract_rejects_unknown_action(tmp_path: Path) -> None:
    payload = _run_contract(tmp_path, {"action": "write_surface"})
    assert payload["status"] == "error"
    assert "Unknown action" in payload["reason"]


def test_owner_contract_ignores_parent_python_runtime_overrides(tmp_path: Path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "01 - Optimizer"
    runtime_root = MODULE_ROOT / "runtime" / "python"

    monkeypatch.setenv("PYTHONHOME", str(runtime_root.resolve()))
    monkeypatch.setenv("PYTHONPATH", str(MODULE_ROOT.resolve()))
    monkeypatch.setenv("VIRTUAL_ENV", str((MODULE_ROOT / "dev-tests" / ".venv").resolve()))
    monkeypatch.setenv("__PYVENV_LAUNCHER__", str((runtime_root / "python.exe").resolve()))
    monkeypatch.setenv("TCL_LIBRARY", str((runtime_root / "tcl" / "tcl8.6").resolve()))
    monkeypatch.setenv("TK_LIBRARY", str((runtime_root / "tcl" / "tk8.6").resolve()))
    monkeypatch.setenv("OPTIMIZER_HOME", str(tmp_path / "optimizer_home"))

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "ingestion_layer_vision" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "read_surface", "surface_id": "optimizer.settings"},
    )

    assert payload["status"] == "ok"
    assert payload["surface_id"] == "optimizer.settings"
    assert payload["value"]["parallel_workers"] == 4


def test_optimizer_owner_contract_ignores_parent_python_runtime_overrides(tmp_path: Path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "01 - Optimizer"
    runtime_root = MODULE_ROOT / "runtime" / "python"

    monkeypatch.setenv("PYTHONHOME", str(runtime_root.resolve()))
    monkeypatch.setenv("PYTHONPATH", str(MODULE_ROOT.resolve()))
    monkeypatch.setenv("VIRTUAL_ENV", str((MODULE_ROOT / "dev-tests" / ".venv").resolve()))
    monkeypatch.setenv("__PYVENV_LAUNCHER__", str((runtime_root / "python.exe").resolve()))
    monkeypatch.setenv("TCL_LIBRARY", str((runtime_root / "tcl" / "tcl8.6").resolve()))
    monkeypatch.setenv("TK_LIBRARY", str((runtime_root / "tcl" / "tk8.6").resolve()))
    monkeypatch.setenv("OPTIMIZER_HOME", str(tmp_path / "optimizer_home"))

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "ingestion_layer_vision" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "read_surface", "surface_id": "optimizer.debug_capabilities"},
    )

    assert payload["status"] == "ok"
    assert payload["surface_id"] == "optimizer.debug_capabilities"
    assert payload["value"]["module_key"] == "optimizer"


def test_contract_runtime_rejects_non_object_response(tmp_path: Path, monkeypatch) -> None:
    state_root = tmp_path / "state"
    module_root = tmp_path / "owner"
    module_root.mkdir()
    monkeypatch.setattr(runtime_adapter, "_contract_python", lambda _module_root: Path(sys.executable))

    def fake_run(args, **_kwargs):
        Path(args[-1]).write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runtime_adapter.subprocess, "run", fake_run)

    try:
        runtime_adapter.invoke_module_contract(
            module_root=module_root,
            contract_module="owner.edit_contract",
            state_root=state_root,
            payload={"action": "healthcheck"},
        )
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("Owner contract responses must be JSON objects")


def test_contract_runtime_times_out_owner_contract(tmp_path: Path, monkeypatch) -> None:
    state_root = tmp_path / "state"
    module_root = tmp_path / "owner"
    module_root.mkdir()
    monkeypatch.setattr(runtime_adapter, "_contract_python", lambda _module_root: Path(sys.executable))

    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(runtime_adapter.subprocess, "run", fake_run)

    try:
        runtime_adapter.invoke_module_contract(
            module_root=module_root,
            contract_module="owner.edit_contract",
            state_root=state_root,
            payload={"action": "healthcheck"},
            timeout_seconds=1,
        )
    except RuntimeError as exc:
        assert "timed out after 1 seconds" in str(exc)
    else:
        raise AssertionError("Owner contract timeouts must be surfaced")


def test_contract_runtime_cleans_stale_temp_dirs(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    stale = state_root / "edit-contract-stale"
    recent = state_root / "edit-contract-recent"
    stale.mkdir(parents=True)
    recent.mkdir()
    old = time.time() - 120
    stale_ts = old
    recent_ts = time.time()
    # Windows updates directory mtimes through children, so set them after creation.
    import os

    os.utime(stale, (stale_ts, stale_ts))
    os.utime(recent, (recent_ts, recent_ts))

    runtime_adapter.cleanup_stale_contract_tempdirs(state_root, max_age_seconds=60)

    assert not stale.exists()
    assert recent.exists()


def test_contract_timeout_env_override_fails_closed_when_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS", "not-an-int")

    with pytest.raises(ValueError, match="must be an integer"):
        runtime_adapter._contract_timeout_seconds(None)


def test_contract_timeout_env_override_requires_positive_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValueError, match="at least 1 second"):
        runtime_adapter._contract_timeout_seconds(None)


def test_contract_timeout_explicit_override_requires_positive_seconds() -> None:
    with pytest.raises(ValueError, match="at least 1 second"):
        runtime_adapter._contract_timeout_seconds(0)


def test_contract_python_candidate_must_be_file(tmp_path: Path) -> None:
    module_root = tmp_path / "owner"
    (module_root / "runtime" / "python" / "python.exe").mkdir(parents=True)
    runtime_adapter._contract_python_cached.cache_clear()

    with pytest.raises(FileNotFoundError, match="No module runtime"):
        runtime_adapter._contract_python(module_root)

