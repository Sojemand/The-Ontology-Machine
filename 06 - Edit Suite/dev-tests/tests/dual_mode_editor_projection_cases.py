from __future__ import annotations

from types import SimpleNamespace

from edit_suite.ui import taxonomy_release_editor

from dual_mode_editor_support import Entry, TextBox, Var, picker


def test_taxonomy_release_projection_picker_values_replace_free_text_codes() -> None:
    widget = SimpleNamespace(
        _draft={
            "schema_version": "taxonomy_release_draft.v1",
            "artifact_root": "",
            "release_candidates": [],
            "selected_release_path": "",
            "working_release_path": "",
            "corpus_db_path": "",
            "origin": {},
            "verification": {"status": "draft_loaded"},
            "release": {
                "master_taxonomy": {
                    "domains": [{"id": "finance"}, {"id": "administrative"}],
                    "document_types": [{"code": "invoice"}, {"code": "statement"}],
                    "categories": [{"code": "finance"}],
                    "subcategories": [{"code": "invoice"}],
                    "field_codes": [{"code": "issuer"}, {"code": "amount_due"}],
                    "row_types": [{"code": "line_item"}],
                    "cell_codes": [{"code": "amount"}],
                    "role_types": [{"code": "issuer"}, {"code": "recipient"}],
                },
                "projections": [
                    {
                        "projection_id": "finance.default.v1",
                        "label": "Finance",
                        "description": "",
                        "domain_ids": ["invented_domain"],
                        "include_document_types": ["made_up_doc"],
                        "include_categories": [],
                        "include_subcategories": [],
                        "include_field_codes": ["invented_field"],
                        "include_row_types": [],
                        "include_cell_codes": [],
                        "routing": {
                            "when_to_use": "",
                            "avoid_when": "",
                            "example_document_types": ["made_up_doc"],
                            "section_roles": [],
                            "party_roles": [],
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
        _artifact_root_entry=Entry(""),
        _working_release_entry=Entry(""),
        _corpus_db_entry=Entry(""),
        _candidate_var=Var(""),
        _candidate_labels={},
        _taxonomy_section=Var("domains"),
        _selected_taxonomy_index=0,
        _taxonomy_widgets={
            "key": Entry("finance"),
            "label": Entry(""),
            "description": Entry(""),
            "aliases": Entry(""),
            "status": Entry(""),
            "parent_id": Entry(""),
        },
        _selected_projection_id="finance.default.v1",
        _projection_widgets={
            "projection_id": Entry("finance.default.v1"),
            "label": Entry("Finance"),
            "description": Entry(""),
            "when_to_use": TextBox("Finance documents"),
            "avoid_when": TextBox(""),
            "text_markers": TextBox("invoice, total"),
        },
        _projection_pickers={
            "domain_ids": picker({"finance", "administrative"}, ["finance", "administrative"]),
            "include_document_types": picker({"invoice", "statement"}, ["invoice", "statement"]),
            "include_categories": picker({"finance"}, ["finance"]),
            "include_subcategories": picker({"invoice"}, ["invoice"]),
            "include_field_codes": picker({"issuer", "amount_due"}, ["issuer", "amount_due"]),
            "include_row_types": picker({"line_item"}, ["line_item"]),
            "include_cell_codes": picker({"amount"}, ["amount"]),
            "example_document_types": picker({"invoice"}, ["invoice", "statement"]),
            "section_roles": picker({"body"}, ["header", "body"]),
            "party_roles": picker({"issuer", "recipient"}, ["issuer", "recipient"]),
        },
    )

    payload = taxonomy_release_editor.read_value(widget)
    projection = payload["release"]["projections"][0]

    assert projection["domain_ids"] == ["finance", "administrative"]
    assert projection["include_document_types"] == ["invoice", "statement"]
    assert projection["include_field_codes"] == ["issuer", "amount_due"]
    assert projection["routing"]["example_document_types"] == ["invoice"]
    assert projection["routing"]["section_roles"] == ["body"]
    assert projection["routing"]["party_roles"] == ["issuer", "recipient"]
    assert projection["routing"]["surface_signals"]["section_roles"] == ["body"]
    assert projection["routing"]["surface_signals"]["party_roles"] == ["issuer", "recipient"]


def test_taxonomy_release_update_choices_syncs_taxonomy_before_rebuilding_pickers(monkeypatch) -> None:
    captured = {}
    widget = SimpleNamespace(
        _draft={
            "release": {
                "master_taxonomy": {
                    "role_types": [{"code": "issuer", "label": "Issuer"}, {"code": "", "label": ""}],
                },
                "projections": [
                    {
                        "projection_id": "finance.default.v1",
                        "label": "Finance",
                        "description": "",
                        "routing": {"surface_signals": {"text_markers": ["invoice"], "domain_markers": {}, "section_roles": [], "party_roles": []}},
                    }
                ],
            }
        },
        _taxonomy_section=Var("role_types"),
        _selected_taxonomy_index=1,
        _taxonomy_widgets={
            "key": Entry("approver"),
            "label": Entry("Approver"),
            "description": Entry(""),
            "aliases": Entry(""),
            "status": Entry(""),
            "parent_id": Entry(""),
        },
        _selected_projection_id="finance.default.v1",
        _projection_widgets={
            "projection_id": Entry("finance.default.v1"),
            "label": Entry("Finance"),
            "description": Entry(""),
            "when_to_use": TextBox("Finance documents"),
            "avoid_when": TextBox(""),
            "text_markers": TextBox("invoice"),
        },
        _projection_pickers={},
    )

    def capture_options(frame, _projection):
        captured["party_roles"] = taxonomy_release_editor._picker_options(frame, "party_roles")

    monkeypatch.setattr(taxonomy_release_editor, "_refresh_projection_pickers", capture_options)

    taxonomy_release_editor._update_projection_choices(widget)

    assert ("approver", "Approver (approver)") in captured["party_roles"]
