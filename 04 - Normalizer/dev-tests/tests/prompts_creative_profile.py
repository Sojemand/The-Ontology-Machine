from __future__ import annotations

from normalizer_vision.taxonomy import build_profile_from_master


def creative_story_profile():
    master = {
        "taxonomy_id": "taxonomy_test",
        "taxonomy_version": "custom.v1",
        "document_types": [
            {"code": "fantasy_short_story", "label": "Fantasy short story", "description": "Fantasy prose."},
            {"code": "other", "label": "Other", "description": "Fallback."},
        ],
        "categories": [
            {"code": "prose_fiction", "label": "Prose fiction", "description": "Fiction."},
            {"code": "other", "label": "Other", "description": "Fallback."},
        ],
        "subcategories": [
            {"code": "afterlife_fantasy", "label": "Afterlife fantasy", "description": "Afterlife fantasy."},
            {"code": "other", "label": "Other", "description": "Fallback."},
        ],
        "field_codes": [
            {"code": "story_title", "label": "Story title", "description": "Title.", "value_type": "string"},
            {"code": "theme", "label": "Theme", "description": "Theme.", "value_type": "string"},
            {"code": "other", "label": "Other", "description": "Fallback.", "value_type": "string"},
        ],
        "row_types": [
            {"code": "narrative_paragraph", "label": "Narrative paragraph", "description": "Narrative."},
            {"code": "other", "label": "Other", "description": "Fallback."},
        ],
        "cell_codes": [
            {"code": "character_reference", "label": "Character reference", "description": "Character."},
            {"code": "other", "label": "Other", "description": "Fallback."},
        ],
        "promotion_slots": [
            {
                "slot": "document_story_title",
                "label": "Story title",
                "description": "Title.",
                "value_type": "string",
                "cardinality": "single",
            },
            {
                "slot": "document_themes",
                "label": "Themes",
                "description": "Themes.",
                "value_type": "string",
                "cardinality": "multi",
            },
        ],
    }
    projection = {
        "projection_id": "creative_writing.fantasy_short_story.v1",
        "label": "Creative story",
        "include_document_types": ["fantasy_short_story", "other"],
        "include_categories": ["prose_fiction", "other"],
        "include_subcategories": ["afterlife_fantasy", "other"],
        "include_field_codes": ["story_title", "theme", "other"],
        "include_row_types": ["narrative_paragraph", "other"],
        "include_cell_codes": ["character_reference", "other"],
        "projection_family": "custom",
        "promotion_rules": [
            {"slot": "document_story_title", "source_paths": ["content.fields.story_title"]},
            {"slot": "document_themes", "source_paths": ["content.fields.theme"]},
        ],
    }
    return build_profile_from_master(master, projection)
