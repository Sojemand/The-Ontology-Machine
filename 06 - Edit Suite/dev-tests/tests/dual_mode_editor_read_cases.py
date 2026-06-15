from __future__ import annotations

from types import SimpleNamespace

from edit_suite.ui import taxonomy_release_editor

from dual_mode_editor_support import Entry, TextBox, Var


def test_taxonomy_release_read_value_updates_structured_draft() -> None:
    widget = SimpleNamespace(
        _draft={
            "schema_version": "taxonomy_release_draft.v1",
            "artifact_root": "old",
            "release_candidates": [],
            "selected_release_path": "",
            "working_release_path": "",
            "corpus_db_path": "",
            "origin": {},
            "verification": {"status": "draft_loaded"},
            "release": {
                "master_taxonomy": {
                    "domains": [{"id": "finance", "label": "Finance", "description": "Old"}],
                },
                "projections": [
                    {
                        "projection_id": "finance.default.v1",
                        "label": "Finance",
                        "description": "",
                        "domain_ids": ["finance"],
                        "include_document_types": ["invoice"],
                        "include_categories": ["finance"],
                        "include_subcategories": ["invoice"],
                        "include_field_codes": ["issuer"],
                        "include_row_types": [],
                        "include_cell_codes": [],
                        "routing": {
                            "when_to_use": "Old routing",
                            "avoid_when": "",
                            "example_document_types": ["invoice"],
                            "surface_signals": {
                                "text_markers": ["invoice"],
                                "domain_markers": {},
                                "section_roles": [],
                                "party_roles": [],
                            },
                        },
                    }
                ],
            },
        },
        _artifact_root_entry=Entry("C:/Artifact Tree"),
        _working_release_entry=Entry("C:/Artifact Tree/Semantic Release/drafts/edit_suite/release.json"),
        _corpus_db_entry=Entry("C:/Artifact Tree/Corpus/current.db"),
        _candidate_var=Var("Release"),
        _candidate_labels={"Release": "C:/Artifact Tree/Semantic Release/releases/default/release.json"},
        _taxonomy_section=Var("domains"),
        _selected_taxonomy_index=0,
        _taxonomy_widgets={
            "key": Entry("finance"),
            "label": Entry("Finance Edited"),
            "description": Entry("Edited domain"),
            "aliases": Entry("money, billing"),
            "status": Entry("active"),
            "parent_id": Entry(""),
        },
        _selected_projection_id="finance.default.v1",
        _projection_widgets={
            "projection_id": Entry("finance.default.v1"),
            "label": Entry("Finance Edited"),
            "description": Entry("Edited projection"),
            "domain_ids": Entry("finance, administrative"),
            "include_document_types": Entry("invoice, statement"),
            "include_categories": Entry("finance"),
            "include_subcategories": Entry("invoice"),
            "include_field_codes": Entry("issuer, amount_due"),
            "include_row_types": Entry(""),
            "include_cell_codes": Entry(""),
            "when_to_use": TextBox("Use for finance documents"),
            "avoid_when": TextBox("Avoid for contracts"),
            "example_document_types": TextBox("invoice, statement"),
            "text_markers": TextBox("invoice, total"),
            "section_roles": TextBox("body"),
            "party_roles": TextBox("issuer, recipient"),
        },
    )

    payload = taxonomy_release_editor.read_value(widget)

    assert payload["artifact_root"] == "C:/Artifact Tree"
    assert payload["selected_release_path"].endswith("release.json")
    assert payload["release"]["master_taxonomy"]["domains"][0]["label"] == "Finance Edited"
    assert payload["release"]["master_taxonomy"]["domains"][0]["aliases"] == ["money", "billing"]
    projection = payload["release"]["projections"][0]
    assert projection["label"] == "Finance Edited"
    assert projection["include_field_codes"] == ["issuer", "amount_due"]
    assert projection["routing"]["surface_signals"]["text_markers"] == ["invoice", "total"]
