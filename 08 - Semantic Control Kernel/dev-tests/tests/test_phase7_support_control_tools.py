from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.agent_tool_invocation_service import AgentToolInvocationService
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.types.state import WorkflowResumeState


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"
TARGET = {"target_hash": "target_phase7"}


def test_kernel_status_and_resume_state_are_read_only_against_phase3_stores(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    resume_store = WorkflowResumeStore(paths)
    interaction_store = InteractionRequestStore(paths)
    resume_store.put_resume_state(WorkflowResumeState.from_dict(_fixture("kernel.workflow_resume_state.v1")))
    interaction_store.put_pending_interaction(UserInteractionRequest.from_dict(_fixture("kernel.user_interaction_request.v1")))
    before = _snapshot(paths.state_root)

    service = AgentToolInvocationService(state_paths=paths)
    status = service.invoke("kernel_status", invocation_context={}, model_payload={}).to_dict()
    resume = service.invoke("kernel_resume_state", invocation_context={}, model_payload={}).to_dict()

    assert status["active_state"]["resumable_workflow_count"] == 1
    assert status["active_state"]["pending_interaction_count"] == 1
    assert resume["resume_state"]["resumable_count"] == 1
    assert resume["resume_state"]["resumable_workflows"][0]["workflow_ref"].startswith("opaque:")
    assert "workflow_run_id_example" not in json.dumps(resume, sort_keys=True)
    assert _snapshot(paths.state_root) == before


def test_kernel_cancel_active_run_no_active_run_is_read_only_noop(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    before = _snapshot(paths.state_root)

    result = AgentToolInvocationService(state_paths=paths).invoke(
        "kernel_cancel_active_run",
        invocation_context={},
        model_payload={},
    ).to_dict()

    assert result["status"] == "ok"
    assert result["effect"] == "none"
    assert result["cancel_status"] == "no_active_run"
    assert _snapshot(paths.state_root) == before


def test_kernel_cancel_active_run_with_active_run_marks_cancelled_and_stops_processes(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run_store = WorkflowRunStore(paths)
    run = run_store.create_run("manual_pipeline_run", TARGET, "phase7_test", workflow_run_id="wr_cancel_phase7")
    ref_dir = paths.debug_background_continuations_dir / run.workflow_run_id
    ref_dir.mkdir(parents=True)
    (ref_dir / "bgc_phase7.ref.json").write_text(
        json.dumps(
            {
                "schema_version": "kernel.background_continuation_ref.v1",
                "launch_id": "bgc_phase7",
                "mode": "background_process",
                "pid": 4567,
                "workflow_run_id": run.workflow_run_id,
                "workflow_tool": "manual_pipeline_run",
                "started_at": "2026-05-06T00:00:00Z",
                "stdout_ref": "debug/background_continuations/wr_cancel_phase7/bgc_phase7.stdout.json",
                "stderr_ref": "debug/background_continuations/wr_cancel_phase7/bgc_phase7.stderr.txt",
            }
        ),
        encoding="utf-8",
    )

    class Completed:
        returncode = 0
        stdout = "terminated"
        stderr = ""

    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation.os.name", "nt")
    monkeypatch.setattr(
        "semantic_control_kernel.surface.background_continuation.subprocess.run",
        lambda *_args, **_kwargs: Completed(),
    )

    result = AgentToolInvocationService(state_paths=paths).invoke(
        "kernel_cancel_active_run",
        invocation_context={},
        model_payload={},
    ).to_dict()

    assert result["status"] == "ok"
    assert result["effect"] == "write"
    assert result["cancel_status"] == "cancelled"
    assert result["active_state"]["active_workflow_run_count"] == 1
    assert result["active_state"]["background_process_termination"]["terminated"][0]["pid"] == 4567
    assert run_store.list_active_runs() == []
    assert run_store.get_run(run.workflow_run_id).status == "cancelled"


def _fixture(schema_version: str) -> dict:
    return json.loads((FIXTURES / f"{schema_version.replace('.', '__')}.valid.json").read_text(encoding="utf-8"))


def _snapshot(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
