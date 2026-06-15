from __future__ import annotations

from pathlib import Path

from conftest import PIPELINE_ROOT
from edit_suite.contract_runtime import invoke_owner_contract
from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.load_bundle import load_bundle
from edit_suite.surfaces.sections import build_sections


def _entry(module_root: Path) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name="Validator Vision",
        module_root=str(module_root.resolve()),
        module_key="validator",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "validator_vision" / "edit_contract").resolve()),
        runtime_available=True,
    )


def test_validator_owner_contract_reads_flat_settings_slice(tmp_path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "03 - Validator"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(tmp_path / "validator_home"))

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "validator_vision" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "read_surface", "surface_id": "validator.settings"},
    )

    assert payload["status"] == "ok"
    assert payload["surface_id"] == "validator.settings"
    assert payload["value"]["checks.free_text"] is True
    assert payload["value"]["match.row_level"] == "WARN"


def test_validator_bundle_maps_into_settings_and_operations_sections(tmp_path, monkeypatch) -> None:
    module_root = PIPELINE_ROOT / "03 - Validator"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(tmp_path / "validator_home"))
    entry = _entry(module_root)

    bundle = load_bundle(entry, state_root=tmp_path / "state")
    sections = {section.name: section for section in build_sections(entry, bundle, {})}

    assert bundle.module_summary.startswith("VALIDATOR HELP")
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == [
        "validator.settings",
        "validator.report_preview_policy",
    ]
    assert [surface.surface_id for surface in sections["Operations"].surfaces] == [
        "validator.debug_capabilities",
    ]
