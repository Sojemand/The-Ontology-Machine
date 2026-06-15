from __future__ import annotations

from tests.tool_contract_matrix_helpers import _artifact_args, _reset_workspace_paths, _support_incident, _working_workspace_paths, _workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "derive_working_release_from_blueprint",
            lambda p: {
                "artifact_folder": p["working_workspace_artifact_root"],
                "blueprint_ref": "default",
                "target_release_id": "semantic_release.default",
                "target_release_version": "2026-04-05.default",
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "derive_working_release_from_blueprint",
                        "blueprint_ref": "default",
                        "target_release_id": "semantic_release.default",
                        "target_release_version": "2026-04-05.default",
                    },
                )
            ],
        ),
        GoldenCase(
            "create_minimal_custom_release",
            lambda _p: {
                "artifact_folder": _p["working_workspace_artifact_root"],
                "language": "de",
                "projection_id": "fantasy.story.custom.v1",
                "archive_label": "Fantasy Story Spezialarchiv",
                "archive_description": "Kleines Spezialarchiv fuer Fantasy-Kapitel, Figuren, Orte, Lore und Szenen.",
                "domain": {"code": "fantasy", "label": "Fantasy", "description": "Fantasy- und Story-Material."},
                "category": {"code": "story", "label": "Story", "description": "Erzaehlende Story-Inhalte."},
                "subcategory": {"code": "lore", "label": "Lore", "description": "Lore und Weltbau."},
                "document_types": [{"code": "story_chapter", "label": "Story Chapter", "description": "Kapitel oder Szene."}],
                "field_codes": [{"code": "character", "label": "Character", "description": "Figur im Text."}],
                "text_markers": ["fantasy", "chapter", "character", "lore"],
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "create_minimal_custom_release",
                        "language": "de",
                        "release_id": "semantic_release.fantasy.story.custom.v1",
                        "projection_id": "fantasy.story.custom.v1",
                        "archive_label": "Fantasy Story Spezialarchiv",
                        "archive_description": "Kleines Spezialarchiv fuer Fantasy-Kapitel, Figuren, Orte, Lore und Szenen.",
                        "domain": {"code": "fantasy", "label": "Fantasy", "description": "Fantasy- und Story-Material."},
                        "category": {"code": "story", "label": "Story", "description": "Erzaehlende Story-Inhalte."},
                        "subcategory": {"code": "lore", "label": "Lore", "description": "Lore und Weltbau."},
                        "document_types": [{"code": "story_chapter", "label": "Story Chapter", "description": "Kapitel oder Szene."}],
                        "field_codes": [{"code": "character", "label": "Character", "description": "Figur im Text."}],
                        "text_markers": ["fantasy", "chapter", "character", "lore"],
                    },
                )
            ],
        ),
        GoldenCase(
            "create_projection_draft",
            lambda _p: {
                "artifact_folder": _p["working_workspace_artifact_root"],
                "projection_id": "fantasy.story.default.v1",
                "template_projection_id": "personal.expression.default.v1",
                "language": "de",
                "label": "Fantasy Story",
                "description": "Profil fuer Story-Notizen, Figuren, Lore und Kapitelplanung.",
                "when_to_use": "Nutzen fuer Fantasy-, Story-, Figuren- und Lore-Dokumente.",
                "avoid_when": "Nicht fuer Rechnungen, Behoerdenpost oder medizinische Dokumente.",
                "example_document_types": "story_notes\ncharacter_sheet\nchapter_outline",
                "text_markers": "lore, figur, kapitel",
                "primary_domain": "personal",
                "domain_ids": "personal, people, other",
                "include_document_types": "narrative_text, profile, other",
                "include_categories": "personal, people, other",
                "include_subcategories": "creative_writing, general_correspondence, other",
                "include_field_codes": "person_name, document_date, subject, event_name, other",
                "include_row_types": "timeline_entry, participant_list, other",
                "include_cell_codes": "description, scheduled_date, note, name, participant_role, other",
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "create_projection_draft",
                        "projection_id": "fantasy.story.default.v1",
                        "template_projection_id": "personal.expression.default.v1",
                        "locale": "de",
                        "label": "Fantasy Story",
                        "description": "Profil fuer Story-Notizen, Figuren, Lore und Kapitelplanung.",
                        "when_to_use": "Nutzen fuer Fantasy-, Story-, Figuren- und Lore-Dokumente.",
                        "avoid_when": "Nicht fuer Rechnungen, Behoerdenpost oder medizinische Dokumente.",
                        "example_document_types": "story_notes\ncharacter_sheet\nchapter_outline",
                        "text_markers": "lore, figur, kapitel",
                        "primary_domain": "personal",
                        "domain_ids": "personal, people, other",
                        "include_document_types": "narrative_text, profile, other",
                        "include_categories": "personal, people, other",
                        "include_subcategories": "creative_writing, general_correspondence, other",
                        "include_field_codes": "person_name, document_date, subject, event_name, other",
                        "include_row_types": "timeline_entry, participant_list, other",
                        "include_cell_codes": "description, scheduled_date, note, name, participant_role, other",
                    },
                )
            ],
        ),
        GoldenCase(
            "generate_locale_translation_payload",
            lambda _p: {
                "artifact_folder": _p["working_workspace_artifact_root"],
                "source_language": "de",
                "target_language": "en",
                "model": "gpt-5.4-mini",
                "max_output_tokens": 16000,
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "generate_locale_translation_payload",
                        "source_locale": "de",
                        "target_locale": "en",
                        "model": "gpt-5.4-mini",
                        "max_output_tokens": 16000,
                    },
                )
            ],
        ),
        GoldenCase(
            "translate_working_release_locale",
            lambda _p: {
                "artifact_folder": _p["working_workspace_artifact_root"],
                "source_locale": "de",
                "target_locale": "en",
                "translation_payload": {
                    "master": {"description": "Translated master"},
                    "projections": {
                        "finance.default.v1": {"label": "Finance"},
                        "fantasy.story.default.v1": {"label": "Fantasy Story"},
                    },
                },
                "overwrite_existing": True,
            },
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "translate_release_locale",
                        "source_locale": "de",
                        "target_locale": "en",
                        "translation_payload": {
                            "master": {"description": "Translated master"},
                            "projections": {
                                "finance.default.v1": {"label": "Finance"},
                                "fantasy.story.default.v1": {"label": "Fantasy Story"},
                            },
                        },
                        "overwrite_existing": True,
                    },
                )
            ],
        ),
        GoldenCase(
            "inspect_active_corpus",
            lambda p: {"corpus_db_path": p["active_db"]},
            product_calls=lambda p: [("corpus_builder", {"action": "semantic_status", "corpus_db_path": p["active_db"]})],
        ),
        GoldenCase(
            "activate_corpus_context",
            lambda p: {"corpus_db_path": p["active_db"], "corpus_output_folder": p["corpus_root"]},
            product_calls=lambda p: [
                ("corpus_builder", {"action": "activate_corpus_context", "corpus_db_path": p["active_db"]}),
                (
                    "orchestrator",
                    {
                        "action": "activate_corpus_context",
                        "corpus_db_path": p["active_db"],
                        "corpus_output_folder": p["corpus_root"],
                    },
                ),
            ],
        ),
    ]
