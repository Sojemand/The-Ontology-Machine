from __future__ import annotations

import json
from pathlib import Path

from orchestrator.debug_host import registry, workflow
from orchestrator.debug_host.types import DebugPlan, DebugProcessHandle, DebugStep
from tests.debug_host_test_support import write_debug_registry

MODULE_ROOT = Path(__file__).resolve().parents[2]
REAL_REGISTRY_PATH = MODULE_ROOT / "module-registry.json"


class _DoneProcess:
    def poll(self):
        return 0


def test_refresh_advances_into_request_enrichment_host_step(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path)
    input_root = tmp_path / "input"
    source_path = input_root / "invoice.pdf"
    input_root.mkdir()
    source_path.write_text("pdf", encoding="utf-8")
    monkeypatch.setattr(
        "orchestrator.debug_host.workflow.launcher.launch_process",
        lambda *args, **kwargs: DebugProcessHandle(process=_DoneProcess(), request_path=Path("request.json"), response_path=Path("response.json")),
    )
    descriptor = registry.descriptor_for("optimizer", registry_path=registry_path)
    plan = DebugPlan("two-step", (DebugStep.module("optimizer", "debug_run"), DebugStep.host("request_enrichment")))
    session = workflow.start(
        "optimizer",
        "single",
        input_root,
        source_path="invoice.pdf",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        descriptor=descriptor,
        plan=plan,
        options={"filters": {}, "worker_count": 1},
    )
    _write_optimizer_outputs(session, nested_root="")

    def fake_build_working_request(_modules, **kwargs):  # noqa: ANN001
        assert kwargs["projection_catalog"]["catalog_version"] == "sha256:debug"
        kwargs["request_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["request_path"].write_text(json.dumps({"request": "ok"}), encoding="utf-8")
        return {"status": "ok", "request_path": str(kwargs["request_path"])}

    monkeypatch.setattr(
        "orchestrator.debug_host.request_enrichment_steps.request_enrichment.build_working_request",
        fake_build_working_request,
    )
    monkeypatch.setattr(
        "orchestrator.debug_host.request_enrichment_steps.load_normalizer_projection_catalog",
        lambda _modules: {"catalog_version": "sha256:debug", "master_taxonomy_version": "v1", "projections": []},
    )

    session = workflow.refresh(session, modules=object())

    assert session.active_step is None
    assert session.result is not None
    assert session.result.artifacts["interpreter_request"] == ["outputs/requests/invoice.pdf/interpreter.request.json"]
    assert session.result.outputs["interpreter_request"] == ["outputs/requests/invoice.pdf/interpreter.request.json"]


def test_request_enrichment_fails_closed_without_modules(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path)
    input_root = tmp_path / "input"
    input_root.mkdir()
    monkeypatch.setattr(
        "orchestrator.debug_host.workflow.launcher.launch_process",
        lambda *args, **kwargs: DebugProcessHandle(process=type("_P", (), {"poll": lambda self: None})(), request_path=Path("request.json"), response_path=Path("response.json")),
    )
    descriptor = registry.descriptor_for("optimizer", registry_path=registry_path)
    plan = DebugPlan("host-only", (DebugStep.host("request_enrichment"),))

    session = workflow.start(
        "optimizer",
        "single",
        input_root,
        state_root=tmp_path / "state",
        registry_path=registry_path,
        descriptor=descriptor,
        plan=plan,
        options={},
    )

    assert session.result is not None
    assert session.result.status == "error"
    assert session.result.error == "Missing prerequisites"


def test_refresh_stops_after_host_step_error(tmp_path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_interpreter=True)
    input_root = tmp_path / "input"
    source_path = input_root / "invoice.pdf"
    input_root.mkdir()
    source_path.write_text("pdf", encoding="utf-8")
    launches = []

    def fake_launch(*args, **kwargs):  # noqa: ANN002, ANN003
        launches.append((args, kwargs))
        return DebugProcessHandle(process=_DoneProcess(), request_path=Path("request.json"), response_path=Path("response.json"))

    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch)

    descriptor = registry.descriptor_for("interpreter", registry_path=registry_path)
    plan = DebugPlan(
        "three-step",
        (
            DebugStep.module("optimizer", "debug_run"),
            DebugStep.host("request_enrichment"),
            DebugStep.module("interpreter", "debug_run"),
        ),
    )
    session = workflow.start(
        "interpreter",
        "single",
        input_root,
        source_path="invoice.pdf",
        state_root=tmp_path / "state",
        registry_path=registry_path,
        descriptor=descriptor,
        plan=plan,
        options={"filters": {}, "worker_count": 1},
    )
    _write_optimizer_outputs(session, nested_root="")

    session = workflow.refresh(session, modules=None)

    assert len(launches) == 1
    assert session.active_step is None
    assert session.result is not None
    assert session.result.status == "error"
    assert session.result.error == "Missing prerequisites"



def _write_optimizer_outputs(session, *, nested_root: str) -> None:
    raw_path = session.output_root / "raw_extracts" / nested_root / "invoice.raw.json"
    page_path = session.output_root / "page_assets" / nested_root / "invoice" / "page_001.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}", encoding="utf-8")
    page_path.write_text("png", encoding="utf-8")
    raw_output = "outputs/raw_extracts/invoice.raw.json" if not nested_root else f"outputs/raw_extracts/{nested_root}/invoice.raw.json"
    page_output = "outputs/page_assets/invoice/page_001.png" if not nested_root else f"outputs/page_assets/{nested_root}/invoice/page_001.png"
    session.result_path.write_text(
        json.dumps({"status": "ok", "summary": "done", "outputs": {"raw_extracts": [raw_output], "page_assets": [page_output]}}),
        encoding="utf-8",
    )

