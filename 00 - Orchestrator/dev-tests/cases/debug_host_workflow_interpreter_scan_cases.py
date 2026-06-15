from __future__ import annotations

from types import SimpleNamespace

from orchestrator.debug_host import workflow
from orchestrator.debug_host.types import DebugProcessHandle
from orchestrator.models import RuntimeSettingsState
from tests.debug_host_test_support import write_debug_registry

from .debug_host_workflow_interpreter_support import _Process


def test_interpreter_scan_launches_optimizer_scan_only(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    launches: list[dict[str, object]] = []

    def fake_launch(spec, payload, *, request_path, response_path, env_overlay=None, bootstrap_home=None):  # noqa: ANN001
        launches.append({"spec": spec, "payload": payload, "env_overlay": env_overlay, "bootstrap_home": bootstrap_home})
        return DebugProcessHandle(process=_Process(code=None), request_path=request_path, response_path=response_path)

    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch)

    session = workflow.start(
        "interpreter",
        "scan",
        tmp_path / "input",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        modules=SimpleNamespace(_runtime_settings=RuntimeSettingsState()),
    )

    assert session.active_step is not None
    assert session.active_step.label == "optimizer:scan_debug_input"
    assert launches[0]["payload"] == {
        "action": "scan_debug_input",
        "session_root": str(session.session_root),
        "input_root": str(tmp_path / "input"),
        "mode": "scan",
    }
