from __future__ import annotations

import os
from pathlib import Path

from orchestrator.bootstrap import ModuleRuntimeSpec
from orchestrator.integrations import SubmodulePipelineModules


def _runtime_spec(tmp_path: Path) -> ModuleRuntimeSpec:
    module_root = tmp_path / "validator"
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    python_exe = runtime_dir / ("python.exe" if os.name == "nt" else "python")
    python_exe.write_text("", encoding="utf-8")
    manifest_path = module_root / "module-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    return ModuleRuntimeSpec(
        key="validator",
        display_name="Validator",
        module_root=module_root,
        contract_module="demo.contract",
        runtime_dir=runtime_dir,
        python_executable=python_exe,
        manifest_path=manifest_path,
        actions=("healthcheck",),
    )


def test_validate_document_includes_optional_raw_path(tmp_path: Path, monkeypatch) -> None:
    modules = object.__new__(SubmodulePipelineModules)
    modules._runtime_specs = {"validator": _runtime_spec(tmp_path)}
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"status": "PASS", "report_path": "report.json"}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.validate_document(
        tmp_path / "doc.structured.json",
        tmp_path / "validation" / "doc.files_validation_report.json",
        raw_path=tmp_path / "doc.raw.json",
    )

    assert captured["module_key"] == "validator"
    assert captured["timeout"] == 600
    assert captured["payload"] == {
        "action": "validate_document",
        "structured_path": str(tmp_path / "doc.structured.json"),
        "validation_output_path": str(tmp_path / "validation" / "doc.files_validation_report.json"),
        "raw_path": str(tmp_path / "doc.raw.json"),
    }
