from __future__ import annotations

from pathlib import Path

from edit_suite.surfaces.sections import build_sections
from surfaces_support import bundle_workflow, entry


def test_load_bundle_keeps_owner_summary_cards_and_builds_operation_surfaces(tmp_path: Path, monkeypatch) -> None:
    descriptors = (
        {
            "surface_id": "corpus_builder.search_policy",
            "label": "Search Policy",
            "kind": "policy",
            "editable": True,
            "source_path": "config/search_policy.json",
            "section": "Settings",
            "action_buttons": [
                {
                    "action": "search",
                    "label": "Search Corpus",
                    "contract_module": "corpus_builder.orchestrator_contract",
                    "inputs": [{"name": "query", "label": "Query", "field_type": "text", "required": True}],
                }
            ],
        },
    )

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        if payload["action"] == "describe_surfaces":
            return {
                "status": "ok",
                "surfaces": descriptors,
                "module_summary": "summary",
                "summary_cards": [{"card_id": "status", "label": "Status", "body": "body", "lines": ["one", "two"]}],
            }
        return {"status": "ok", "value": {"fulltext.limit_default": 20}}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)

    bundle = bundle_workflow.load_bundle(entry(), state_root=tmp_path)
    sections = {section.name: section for section in build_sections(entry(), bundle, {})}

    assert bundle.summary_cards[0].label == "Status"
    assert sections["Summary"].summary_cards[0].lines == ("one", "two")
    assert sections["Operations"].surfaces[0].surface_id.endswith("::action::search")
    assert sections["Operations"].surfaces[0].editor_kind == "operation"
