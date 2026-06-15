from __future__ import annotations

from pathlib import Path

from conftest import MODULE_ROOT, PIPELINE_ROOT
from edit_suite.contract_runtime import invoke_owner_contract
from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.load_bundle import load_bundle
from edit_suite.surfaces.sections import build_sections


def _entry(module_root: Path) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name="Interpreter",
        module_root=str(module_root.resolve()),
        module_key="interpreter",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "llm_interpreter" / "edit_contract").resolve()),
        runtime_available=True,
    )


def _optimizer_entry(module_root: Path) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name="Optimizer",
        module_root=str(module_root.resolve()),
        module_key="optimizer",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "ingestion_layer_vision" / "edit_contract").resolve()),
        runtime_available=True,
    )


def test_interpreter_vision_owner_contract_ignores_parent_python_runtime_overrides(tmp_path: Path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "02 - Interpreter"
    runtime_root = MODULE_ROOT / "runtime" / "python"

    monkeypatch.setenv("PYTHONHOME", str(runtime_root.resolve()))
    monkeypatch.setenv("PYTHONPATH", str(MODULE_ROOT.resolve()))
    monkeypatch.setenv("VIRTUAL_ENV", str((MODULE_ROOT / "dev-tests" / ".venv").resolve()))
    monkeypatch.setenv("__PYVENV_LAUNCHER__", str((runtime_root / "python.exe").resolve()))
    monkeypatch.setenv("TCL_LIBRARY", str((runtime_root / "tcl" / "tcl8.6").resolve()))
    monkeypatch.setenv("TK_LIBRARY", str((runtime_root / "tcl" / "tk8.6").resolve()))
    monkeypatch.setenv("INTERPRETER_VISION_HOME", str(tmp_path / "interpreter_vision_home"))

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "llm_interpreter" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "read_surface", "surface_id": "interpreter.runtime_policy_env"},
    )

    assert payload["status"] == "ok"
    assert payload["surface_id"] == "interpreter.runtime_policy_env"
    assert payload["value"]["OPENAI_API_BASE_URL"] == "https://api.openai.com/v1"


def test_interpreter_vision_bundle_maps_to_stable_sections_and_keeps_owner_preview(tmp_path: Path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "02 - Interpreter"
    monkeypatch.setenv("INTERPRETER_HOME", str(tmp_path / "interpreter_home"))
    entry = _entry(module_root)

    bundle = load_bundle(entry, state_root=tmp_path / "state")
    sections = {section.name: section for section in build_sections(entry, bundle, {})}
    prompt_surface = next(surface for surface in bundle.surfaces if surface.surface_id == "interpreter.prompt_bundle")

    assert bundle.module_summary.startswith("INTERPRETER HELP")
    assert prompt_surface.editor_kind == "prompt_bundle"
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == [
        "interpreter.runtime_policy_env",
        "interpreter.execution_limits",
    ]
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == [
        "interpreter.prompt_bundle",
    ]
    assert [surface.surface_id for surface in sections["Operations"].surfaces] == [
        "interpreter.debug_capabilities",
    ]
    preview_ids = [surface.surface_id for surface in sections["Preview/Drift"].surfaces]
    assert preview_ids[0] == "interpreter.output_contract_preview"
    assert preview_ids.count("interpreter.output_contract_preview") == 2


def test_optimizer_bundle_uses_form_groups_and_keeps_owner_preview(tmp_path: Path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "01 - Optimizer"
    monkeypatch.setenv("OPTIMIZER_HOME", str(tmp_path / "optimizer_home"))
    entry = _optimizer_entry(module_root)

    bundle = load_bundle(entry, state_root=tmp_path / "state")
    sections = {section.name: section for section in build_sections(entry, bundle, {})}
    settings_surface = next(surface for surface in bundle.surfaces if surface.surface_id == "optimizer.settings")

    assert bundle.module_summary.startswith("OPTIMIZER HELP")
    assert settings_surface.editor_kind == "form"
    assert settings_surface.descriptor["field_groups"] == [
        {"label": "Processing", "fields": ["max_file_size_mb", "max_blocks_per_file", "max_cell_text_length", "processing_order", "plugin_timeout_seconds", "parallel_workers"]},
        {"label": "Rendering/Layout", "fields": ["render_dpi", "render_width_px", "render_height_px", "page_margin_pt", "default_font_size_pt", "code_font_size_pt", "heading_font_size_pt"]},
    ]
    assert settings_surface.value["render_dpi"] == 150
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == ["optimizer.settings"]
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == ["optimizer.ocr_prompt"]
    assert [surface.surface_id for surface in sections["Operations"].surfaces] == ["optimizer.debug_capabilities"]
    preview_ids = [surface.surface_id for surface in sections["Preview/Drift"].surfaces]
    assert preview_ids[0] == "optimizer.output_contract_preview"
    assert preview_ids.count("optimizer.output_contract_preview") == 2

