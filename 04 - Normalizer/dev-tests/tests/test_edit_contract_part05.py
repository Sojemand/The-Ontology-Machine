from tests.edit_contract_shared import *  # noqa: F401,F403

def test_create_minimal_custom_release_replaces_default_master_with_small_custom_package(tmp_project_root: Path) -> None:
    response = source_operations.create_minimal_custom_release(
        tmp_project_root,
        {
            "language": "en",
            "projection_id": "fantasy.story.custom.v1",
            "archive_label": "Fantasy Story Special Archive",
            "archive_description": "Small special archive for fantasy chapters, characters, places, lore, and scenes.",
            "domain": {"code": "fantasy", "label": "Fantasy", "description": "Fantasy and story material."},
            "category": {"code": "story", "label": "Story", "description": "Narrative story content."},
            "subcategory": {"code": "lore", "label": "Lore and Scenes", "description": "Lore, scenes, and worldbuilding."},
            "document_types": [
                {"code": "story_chapter", "label": "Story Chapter", "description": "Chapters or scenes from a fantasy story."}
            ],
            "field_codes": [
                {"code": "title", "label": "Title", "description": "Title of the text.", "promotion_slot": "story_title"},
                {"code": "character", "label": "Character", "description": "Character in the text."},
                {"code": "location", "label": "Location", "description": "Place or setting.", "promotion_slot": "primary_setting"},
                {"code": "lore", "label": "Lore", "description": "Worldbuilding or background information.", "promotion_slot": "fantasy_element", "promotion_cardinality": "multi"},
                {"code": "narrator_voice", "label": "Narrator Voice", "description": "Narrative voice of the text.", "promotion_slot": "narrator_voice"},
                {"code": "summary", "label": "Summary", "description": "Short content summary."},
            ],
            "row_types": [
                {"code": "scene_event", "label": "Scene Event", "description": "Important event in a scene."}
            ],
            "cell_codes": [
                {"code": "name", "label": "Name", "description": "Name."},
                {"code": "description", "label": "Description", "description": "Beschreibung."},
            ],
            "text_markers": ["fantasy", "chapter", "scene", "character", "lore", "worldbuilding"],
            "when_to_use": "For fantasy chapters, scenes, characters, places, lore, and worldbuilding.",
            "avoid_when": "Not for general administration or invoice documents.",
        },
    )
    validate = source_operations.validate_release_package(tmp_project_root, {"target_locale": "en"})
    compiled = source_operations.compile_release_package(tmp_project_root, {"target_locale": "en"})
    master_core = yaml.safe_load(
        (
            tmp_project_root
            / "config"
            / "taxonomy_sources"
            / "semantic_release.default"
            / "master.core.yaml"
        ).read_text(encoding="utf-8")
    )
    projection_core = yaml.safe_load(
        (
            tmp_project_root
            / "config"
            / "taxonomy_sources"
            / "semantic_release.default"
            / "projections"
            / "fantasy.story.custom.v1.core.yaml"
        ).read_text(encoding="utf-8")
    )

    assert response["status"] == "ok"
    assert response["value"]["term_counts"]["document_types"] == 2
    assert response["value"]["term_counts"]["field_codes"] == 7
    assert validate["status"] == "ok"
    assert compiled["status"] == "ok"
    assert sorted(master_core["domains"]) == ["fantasy", "other"]
    assert sorted(master_core["document_types"]) == ["other", "story_chapter"]
    assert sorted(master_core["field_codes"]) == ["character", "location", "lore", "narrator_voice", "other", "summary", "title"]
    assert [item["slot"] for item in master_core["promotion_slots"]] == ["story_title", "primary_setting", "fantasy_element", "narrator_voice"]
    assert "document_title" not in {item["slot"] for item in master_core["promotion_slots"]}
    assert "promotion_slot" not in master_core["field_codes"]["location"]
    assert projection_core["include_document_types"] == ["story_chapter", "other"]
    assert projection_core["include_field_codes"] == ["title", "character", "location", "lore", "narrator_voice", "summary", "other"]
    assert projection_core["promotion_rules"] == [
        {"slot": "story_title", "source_paths": ["content.fields.title"]},
        {"slot": "primary_setting", "source_paths": ["content.fields.location"]},
        {"slot": "fantasy_element", "source_paths": ["content.fields.lore"]},
        {"slot": "narrator_voice", "source_paths": ["content.fields.narrator_voice"]},
    ]

def test_locale_workflow_actions_are_retired_and_non_en_targets_fail_closed(tmp_project_root: Path) -> None:
    retired_action = _run_contract(
        tmp_project_root,
        {"action": "create_locale_scaffold", "source_locale": "en", "target_locale": "fr"},
    )
    assert retired_action["status"] == "error"
    assert "Unbekannte" in retired_action["reason"]
    with pytest.raises(ValueError, match="en-only"):
        source_operations.validate_release_package(
            tmp_project_root,
            {"target_locale": "fr"},
        )
