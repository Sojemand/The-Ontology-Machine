from __future__ import annotations

import json

from orchestrator.debug_host.types import DebugProcessHandle


class Process:
    def __init__(self, code=None) -> None:
        self.code = code

    def poll(self):
        return self.code


_Process = Process


def install_launch_capture(monkeypatch):
    launches: list[dict[str, object]] = []
    first_process = Process(code=0)
    second_process = Process(code=None)

    def fake_launch(spec, payload, *, request_path, response_path, env_overlay=None, bootstrap_home=None):  # noqa: ANN001
        launches.append({"spec": spec, "payload": payload, "env_overlay": env_overlay, "bootstrap_home": bootstrap_home})
        process = first_process if len(launches) == 1 else second_process
        return DebugProcessHandle(process=process, request_path=request_path, response_path=response_path)

    monkeypatch.setattr("orchestrator.debug_host.workflow.launcher.launch_process", fake_launch)
    return launches, first_process, second_process


def install_interpreter_env_overlay(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator.debug_host.steps.env_overlay_for",
        lambda _modules, module_key: {"VISION_OPENAI_AUTH_MODE": "oauth"} if module_key == "interpreter" else None,
    )


def install_projection_catalog(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator.debug_host.request_enrichment_steps.load_normalizer_projection_catalog",
        lambda _modules: {"catalog_version": "sha256:debug", "master_taxonomy_version": "v1", "projections": []},
    )


def write_working_request(kwargs, *, request_value: str = "ok") -> None:  # noqa: ANN001
    kwargs["request_path"].parent.mkdir(parents=True, exist_ok=True)
    kwargs["request_path"].write_text(
        json.dumps({"request": request_value, "context": {"interpreter_profile": "file"}}),
        encoding="utf-8",
    )


def _write_optimizer_result(session) -> None:
    raw_path = session.output_root / "raw_extracts" / "docs" / "invoice.raw.json"
    page_path = session.output_root / "page_assets" / "docs" / "invoice" / "page_001.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}", encoding="utf-8")
    page_path.write_text("png", encoding="utf-8")
    session.result_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "summary": "optimizer done",
                "outputs": {
                    "raw_extracts": ["outputs/raw_extracts/docs/invoice.raw.json"],
                    "page_assets": ["outputs/page_assets/docs/invoice/page_001.png"],
                },
            }
        ),
        encoding="utf-8",
    )


def _write_batch_optimizer_result(session) -> None:
    raw_items = []
    page_items = []
    for name in ("a", "b"):
        raw_path = session.output_root / "raw_extracts" / "batch" / f"{name}.raw.json"
        page_path = session.output_root / "page_assets" / "batch" / name / "page_001.png"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("{}", encoding="utf-8")
        page_path.write_text("png", encoding="utf-8")
        raw_items.append(f"outputs/raw_extracts/batch/{name}.raw.json")
        page_items.append(f"outputs/page_assets/batch/{name}/page_001.png")
    session.result_path.write_text(
        json.dumps({"status": "ok", "summary": "optimizer done", "outputs": {"raw_extracts": raw_items, "page_assets": page_items}}),
        encoding="utf-8",
    )
