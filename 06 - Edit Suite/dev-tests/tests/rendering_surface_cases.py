from __future__ import annotations

from edit_suite.surfaces.types import SurfaceModel
from edit_suite.ui import rendering, slot_hints, surface_cards


def test_summary_section_body_limits_expand_to_full_text_height() -> None:
    body = "\n".join(f"Line {index}" for index in range(1, 19))

    min_lines, max_lines = rendering._section_body_limits("Summary", body)

    assert min_lines == 8
    assert max_lines == 18


def test_non_summary_section_body_limits_stay_compact() -> None:
    min_lines, max_lines = rendering._section_body_limits("Settings", "short body")

    assert (min_lines, max_lines) == (2, 6)


def test_grouped_field_metadata_preserves_explicit_and_remaining_order() -> None:
    surface = SurfaceModel(
        surface_id="optimizer.settings",
        label="Settings",
        kind="settings",
        editable=True,
        editor_kind="form",
        descriptor={
            "field_groups": [
                {"label": "Processing", "fields": ["parallel_workers", "plugin_timeout_seconds"]},
                {"label": "Rendering/Layout", "fields": ["render_dpi"]},
            ]
        },
        value={"parallel_workers": 1, "plugin_timeout_seconds": 120, "render_dpi": 300, "page_margin_pt": 54},
        draft={"parallel_workers": 1, "plugin_timeout_seconds": 120, "render_dpi": 300, "page_margin_pt": 54},
        operation_links=(),
    )

    assert surface_cards._grouped_fields(surface) == [
        ("Processing", ["parallel_workers", "plugin_timeout_seconds"]),
        ("Rendering/Layout", ["render_dpi"]),
        ("", ["page_margin_pt"]),
    ]


def test_prompt_bundle_helpers_keep_readable_section_order() -> None:
    payload = {
        "projection_hint_policy_md": "Projection policy text",
        "output_schema_json": "{\"type\": \"object\"}",
        "user_prompt_rules_md": "User rules text",
        "system_prompt_md": "System prompt text",
    }

    assert surface_cards._prompt_bundle_fields(payload) == [
        ("System Prompt", "system_prompt_md"),
        ("User Prompt", "user_prompt_rules_md"),
        ("Output Schema", "output_schema_json"),
        ("Projection Hint", "projection_hint_policy_md"),
    ]

    actual_text = surface_cards._prompt_bundle_actual_text(payload)

    assert actual_text.index("System Prompt") < actual_text.index("User Prompt")
    assert actual_text.index("User Prompt") < actual_text.index("Output Schema")
    assert actual_text.index("Output Schema") < actual_text.index("Projection Hint")
    assert "System prompt text" in actual_text
    assert "Projection policy text" in actual_text


def test_slot_hint_text_formats_inline_descriptor_metadata() -> None:
    text = slot_hints.slot_hint_text(
        {
            "role": "sprachgebunden",
            "compile_relevance": "authoring_only",
            "allowed_values": ["de"],
            "reference_types": ["existing projection identifiers"],
            "validators": ["taxonomy_sources.validation"],
            "downstream_consumers": ["05 - Corpus Builder"],
            "compile_effect": "No compiled runtime contract.",
            "prompt_effect": "Prompt review only.",
            "corpus_effect": "No corpus effect.",
        }
    )

    assert "sprachgebunden | authoring_only" in text
    assert "Allowed: de" in text
    assert "Refs: existing projection identifiers" in text
    assert "Validators: taxonomy_sources.validation" in text
    assert "Downstream: 05 - Corpus Builder" in text
