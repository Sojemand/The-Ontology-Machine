from __future__ import annotations

import os
from pathlib import Path

from orchestrator.bootstrap import ModuleRuntimeSpec
from orchestrator.integrations import SubmodulePipelineModules
from orchestrator.models import RuntimeSettingsState
from orchestrator.state import load_runtime_settings, save_runtime_settings


def _runtime_spec(tmp_path: Path, module_key: str) -> ModuleRuntimeSpec:
    module_root = tmp_path / module_key
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    python_exe = runtime_dir / ("python.exe" if os.name == "nt" else "python")
    python_exe.write_text("", encoding="utf-8")
    manifest_path = module_root / "module-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    return ModuleRuntimeSpec(
        key=module_key,
        display_name=module_key.replace("_", " ").title(),
        module_root=module_root,
        contract_module="demo.contract",
        runtime_dir=runtime_dir,
        python_executable=python_exe,
        manifest_path=manifest_path,
        actions=("healthcheck",),
    )


def _modules(tmp_path: Path, module_key: str, *, with_state_dir: bool = False) -> SubmodulePipelineModules:
    modules = object.__new__(SubmodulePipelineModules)
    modules._runtime_specs = {module_key: _runtime_spec(tmp_path, module_key)}
    modules._state_dir = (tmp_path / "state") if with_state_dir else None
    return modules


def test_runtime_settings_for_uses_orchestrator_owned_state(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    save_runtime_settings(
        state_dir,
        RuntimeSettingsState.from_dict(
            {
                "schema_version": 1,
                "interpreter": {"model": "gpt-5.4", "max_output_tokens": 8000},
                "normalizer": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
                "optimizer_ocr": {"model": "gpt-5.4", "max_output_tokens": 15000, "timeout_seconds": 120},
                "corpus_builder_embeddings": {"model": "text-embedding-3-large"},
            }
        ),
    )
    modules = object.__new__(SubmodulePipelineModules)
    modules._runtime_specs = {}
    modules._state_dir = state_dir
    modules._runtime_settings = load_runtime_settings(state_dir)

    assert modules._runtime_settings_for("interpreter") == {"model": "gpt-5.4", "max_output_tokens": 8000}
    assert modules._runtime_settings_for("optimizer") == {"model": "gpt-5.4", "max_output_tokens": 15000, "timeout_seconds": 120}
    assert modules._runtime_settings_for("corpus_builder", "generate_embeddings") == {"model": "text-embedding-3-large"}
    assert modules._runtime_settings_for("corpus_builder", "load_document") is None

