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
        display_name="Orchestrator",
        module_root=str(module_root.resolve()),
        module_key="orchestrator",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "orchestrator" / "edit_contract").resolve()),
        runtime_available=True,
    )


def test_orchestrator_owner_contract_describe_surfaces_uses_guided_policy_metadata(tmp_path: Path) -> None:
    module_root = PIPELINE_ROOT / "00 - Orchestrator"

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "orchestrator" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "describe_surfaces"},
    )

    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("ORCHESTRATOR POLICY HELP")
    assert len(payload["summary_cards"]) == 4
    assert [card["label"] for card in payload["summary_cards"]] == [
        "Routing Snapshot",
        "Execution Snapshot",
        "Health Profiles",
        "Artifact Layout",
    ]
    assert [(item["surface_id"], item["editor_kind"], item["section"]) for item in payload["surfaces"]] == [
        ("orchestrator.route_intake_policy", "nested_policy", "Settings"),
        ("orchestrator.execution_policy", "nested_policy", "Settings"),
        ("orchestrator.health_dependency_policy", "nested_policy", "Settings"),
        ("orchestrator.artifact_publication_policy", "nested_policy", "Settings"),
    ]


def test_orchestrator_bundle_maps_guided_policy_surfaces_into_settings(tmp_path: Path) -> None:
    module_root = PIPELINE_ROOT / "00 - Orchestrator"
    entry = _entry(module_root)

    bundle = load_bundle(entry, state_root=tmp_path / "state")
    sections = {section.name: section for section in build_sections(entry, bundle, {})}

    assert bundle.module_summary.startswith("ORCHESTRATOR POLICY HELP")
    assert [card.label for card in sections["Summary"].summary_cards] == [
        "Routing Snapshot",
        "Execution Snapshot",
        "Health Profiles",
        "Artifact Layout",
    ]
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == [
        "orchestrator.route_intake_policy",
        "orchestrator.execution_policy",
        "orchestrator.health_dependency_policy",
        "orchestrator.artifact_publication_policy",
    ]
    assert all(surface.editor_kind == "nested_policy" for surface in sections["Settings"].surfaces)
