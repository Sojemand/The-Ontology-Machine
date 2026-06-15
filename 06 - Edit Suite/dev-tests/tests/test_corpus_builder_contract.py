from __future__ import annotations

import json
from pathlib import Path

from conftest import PIPELINE_ROOT
from edit_suite.contract_runtime import invoke_owner_contract
from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.load_bundle import load_bundle
from edit_suite.surfaces.sections import build_sections


def _entry(module_root: Path) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name="Corpus Builder Vision",
        module_root=str(module_root.resolve()),
        module_key="corpus_builder",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "corpus_builder" / "edit_contract").resolve()),
        runtime_available=True,
    )


def test_corpus_builder_owner_contract_describe_surfaces_uses_as_built_sections(tmp_path: Path) -> None:
    module_root = PIPELINE_ROOT / "05 - Corpus Builder"

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "corpus_builder" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "describe_surfaces"},
    )

    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("CORPUS BUILDER HELP")
    assert len(payload["summary_cards"]) == 4
    assert [card["label"] for card in payload["summary_cards"]] == [
        "Module Role",
        "Release State",
        "Search & Embeddings Readiness",
        "Capabilities & Boundaries",
    ]
    assert [(item["surface_id"], item["section"]) for item in payload["surfaces"]] == [
        ("corpus_builder.settings", "Settings"),
        ("corpus_builder.embeddings_policy", "Settings"),
        ("corpus_builder.search_policy", "Settings"),
    ]


def test_corpus_builder_bundle_maps_to_stable_sections_and_debug_links(tmp_path: Path) -> None:
    module_root = PIPELINE_ROOT / "05 - Corpus Builder"
    entry = _entry(module_root)

    bundle = load_bundle(entry, state_root=tmp_path / "state")
    sections = {section.name: section for section in build_sections(entry, bundle, {})}
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))

    assert bundle.module_summary.startswith("CORPUS BUILDER HELP")
    assert len(sections["Summary"].summary_cards) == 4
    assert [card.label for card in sections["Summary"].summary_cards] == [
        "Module Role",
        "Release State",
        "Search & Embeddings Readiness",
        "Capabilities & Boundaries",
    ]
    release_lines = sections["Summary"].summary_cards[1].lines
    assert any(line.startswith("Published Release: semantic_release.default @") for line in release_lines)
    assert any(line.startswith("Active Release: ") for line in release_lines)
    assert any(line.startswith("Pending Change: ") for line in release_lines)
    assert "Debug Host Only: scan_debug_input, debug_run" in sections["Summary"].summary_cards[3].lines
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == [
        "corpus_builder.settings",
        "corpus_builder.embeddings_policy",
        "corpus_builder.search_policy",
    ]
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == []
    assert any(surface.surface_id.endswith("::action::search") for surface in sections["Operations"].surfaces)
    assert any(surface.surface_id.endswith("::action::preview_rebuild_from_artifacts") for surface in sections["Operations"].surfaces)
    assert any(surface.surface_id.endswith("::action::create_and_activate_new_corpus_db") for surface in sections["Operations"].surfaces)
    assert any(surface.surface_id.endswith("::action::create_and_rebuild_new_corpus_db") for surface in sections["Operations"].surfaces)
    assert any(surface.surface_id.endswith("::action::semantic_status") for surface in sections["Operations"].surfaces)
    assert any(surface.surface_id.endswith("::action::merge_preflight") for surface in sections["Operations"].surfaces)
    assert any(surface.surface_id.endswith("::action::merge_corpus_databases") for surface in sections["Operations"].surfaces)
    operation_actions = [surface.operation_links[0]["action"] for surface in sections["Operations"].surfaces]
    assert set(operation_actions).issubset(set(manifest["actions"]))
