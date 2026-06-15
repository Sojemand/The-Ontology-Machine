from tests.edit_contract_shared import *  # noqa: F401,F403
from normalizer_vision.source_authoring import dispatch_tool

def test_create_projection_draft_creates_full_projection_source_bundle(tmp_project_root: Path) -> None:
    projection_id = "fantasy.lore.draft.v1"
    response = dispatch_tool(
        "create_projection_draft",
        {
            "projection_id": projection_id,
            "template_projection_id": "personal.expression.default.v1",
            "locale": "en",
            "label": "Fantasy Lore v1",
            "description": "Draft projection for lore notes, characters, places, and worldbuilding.",
            "when_to_use": "Lore, character sheets, location notes, and worldbuilding documents.",
            "avoid_when": "Not for invoices, public administration mail, or medical documents.",
            "example_document_types": "general_letter\nreport\nother",
            "text_markers": "lore, character, place, worldbuilding",
            "primary_domain": "personal",
            "domain_ids": "personal, people, other",
            "include_document_types": "general_letter, report, other",
            "include_categories": "personal, people, other",
            "include_subcategories": "creative_writing, self_reflection, other",
            "include_field_codes": "person_name, document_date, subject, other",
            "include_row_types": "timeline_entry, participant_list, other",
            "include_cell_codes": "description, note, name, participant_role, other",
        },
        project_root=tmp_project_root,
    )

    _assert_hint_envelope(response)
    projection = response["value"]["projection"]
    core_path = (
        tmp_project_root
        / "config"
        / "taxonomy_sources"
        / "semantic_release.default"
        / "projections"
        / f"{projection_id}.core.yaml"
    )
    text_path = (
        tmp_project_root
        / "config"
        / "taxonomy_sources"
        / "semantic_release.default"
        / "projections"
        / f"{projection_id}.text.en.yaml"
    )
    core_payload = yaml.safe_load(core_path.read_text(encoding="utf-8"))
    text_payload = yaml.safe_load(text_path.read_text(encoding="utf-8"))

    assert response["status"] == "ok"
    assert response["created_new_projection"] is True
    assert response["locale_resolution"] == {"locale": "en", "source": "explicit_locale"}
    assert response["provenance"] == {
        "operation": "create_projection_draft",
        "projection_id": projection_id,
        "template_projection_id": "personal.expression.default.v1",
        "locale": "en",
        "source": "explicit_projection_draft_inputs",
    }
    assert projection["projection_id"] == projection_id
    assert projection["core"]["routing"]["example_document_types"] == ["general_letter", "report", "other"]
    assert projection["text"]["label"] == "Fantasy Lore v1"
    assert projection["text"]["routing"]["when_to_use"].startswith("Lore")
    assert projection["text"]["routing_lexicon"]["text_markers"] == [
        "lore",
        "character",
        "place",
        "worldbuilding",
    ]
    assert projection["text"]["routing_lexicon"]["domain_markers"]["personal"] == [
        "lore",
        "character",
        "place",
        "worldbuilding",
    ]
    assert core_path.exists()
    assert text_path.exists()
    assert core_payload["projection_id"] == projection_id
    assert core_payload["routing"]["example_document_types"] == ["general_letter", "report", "other"]
    assert set(core_payload["include_document_types"]) >= {"general_letter", "report", "other"}
    assert text_payload["label"] == "Fantasy Lore v1"
    assert text_payload["routing"]["avoid_when"].startswith("Not for invoices")
    assert text_payload["routing_lexicon"]["domain_markers"]["personal"] == [
        "lore",
        "character",
        "place",
        "worldbuilding",
    ]
    assert set(response["generated_files"]) >= {
        f"projections/{projection_id}.core.yaml",
        f"projections/{projection_id}.text.en.yaml",
    }

def test_create_projection_draft_requires_explicit_coverage_for_new_profiles(tmp_project_root: Path) -> None:
    with pytest.raises(ValueError, match="Coverage-Felder"):
        dispatch_tool(
            "create_projection_draft",
            {
                "projection_id": "special.story.draft.v1",
                "template_projection_id": "personal.expression.default.v1",
                "locale": "en",
                "label": "Story",
                "description": "Story profile.",
                "when_to_use": "Story documents.",
                "avoid_when": "Non-story documents.",
                "example_document_types": "other",
            },
            project_root=tmp_project_root,
        )
