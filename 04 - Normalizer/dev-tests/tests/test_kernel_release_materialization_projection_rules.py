from __future__ import annotations

import json

import pytest

from .kernel_release_materialization_support import (
    MODULE_ROOT,
    _custom_taxonomy_ref,
    _owner_request,
    _runtime_profile_fingerprint,
    _story_projection_precursor,
    _story_release_ref,
    dispatch,
)

def test_materialize_semantic_release_candidate_canonicalizes_source_projection_fingerprint(tmp_path: Path) -> None:
    output_path = tmp_path / "source-backed" / "release.json"
    source_projection = _story_projection_precursor()
    source_projection["projection_fingerprint"] = "stale-source-fingerprint"
    source_projection["routing"]["surface_signals"] = {
        "text_markers": ["story"],
        "domain_markers": {"creative_writing": ["story"]},
        "section_roles": ["body"],
        "party_roles": ["other"],
    }
    release_ref = _story_release_ref()
    release_ref["projection_refs"][0]["projection_fingerprint"] = "stale-ref-fingerprint"
    release_ref["projection_refs"][0]["projection_payload"] = source_projection

    result = dispatch(
        "materialize_semantic_release_candidate",
        _owner_request(
            "materialize_semantic_release_candidate",
            output_path=str(output_path),
            release_ref=release_ref,
            projection_update_state={
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [_story_projection_precursor()],
            },
        ),
        project_root=MODULE_ROOT,
    )

    release = json.loads(output_path.read_text(encoding="utf-8"))
    projection_fingerprint = release["projections"][0]["projection_fingerprint"]
    written_projection_ref = result["output_refs"]["release_ref"]["projection_refs"][0]

    assert result["status"] == "ok"
    assert projection_fingerprint not in {"stale-source-fingerprint", "stale-ref-fingerprint"}
    assert _runtime_profile_fingerprint(release) == projection_fingerprint
    assert written_projection_ref["projection_fingerprint"] == projection_fingerprint

def test_custom_taxonomy_materialization_uses_neutral_bindings_for_business_named_codes(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-neutral-bindings" / "release.json"
    taxonomy_ref = _custom_taxonomy_ref()
    taxonomy_ref["field_codes"].append(
        {"code": "owner_name", "domains": ["creative_writing"], "value_type": "string"}
    )
    taxonomy_ref["row_types"].append(
        {"code": "line_item", "domains": ["creative_writing"], "recommended_cell_codes": ["narration_text", "other"]}
    )
    release_ref = _story_release_ref()
    release_ref["taxonomy_ref"] = taxonomy_ref

    result = dispatch(
        "materialize_semantic_release_candidate",
        _owner_request(
            "materialize_semantic_release_candidate",
            output_path=str(output_path),
            release_ref=release_ref,
            projection_update_state={
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [_story_projection_precursor()],
            },
        ),
        project_root=MODULE_ROOT,
    )

    release = json.loads(output_path.read_text(encoding="utf-8"))
    master = release["master_taxonomy"]
    field_by_code = {item["code"]: item for item in master["field_codes"]}
    row_by_code = {item["code"]: item for item in master["row_types"]}

    assert result["status"] == "ok"
    assert field_by_code["owner_name"]["semantic_binding"]["entity_type"] == "document_fact"
    assert field_by_code["owner_name"]["semantic_binding"]["attribute_code"] == "owner_name"
    assert "role_type" not in field_by_code["owner_name"]["semantic_binding"]
    assert row_by_code["line_item"]["semantic_binding"]["entity_type"] == "document_fact"
    assert row_by_code["line_item"]["semantic_binding"]["role_type"] == "line_item"
    assert [item["code"] for item in master["entity_types"]] == ["document_fact"]
    assert "party" not in json.dumps(master, ensure_ascii=False)
    assert "financial_amount" not in json.dumps(master, ensure_ascii=False)

def test_materialize_semantic_release_candidate_rejects_invalid_promotion_rule_source_path(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-invalid-path" / "release.json"
    precursor = _story_projection_precursor()
    precursor["promotion_rules"] = [{"slot": "primary_setting", "source_paths": ["filesystem.primary_setting"]}]

    with pytest.raises(ValueError, match="Source Path"):
        dispatch(
            "materialize_semantic_release_candidate",
            _owner_request(
                "materialize_semantic_release_candidate",
                output_path=str(output_path),
                release_ref=_story_release_ref(),
                projection_update_state={
                    "schema_version": "kernel.create_projections_update_state.input.v1",
                    "projection_precursors": [precursor],
                },
            ),
            project_root=MODULE_ROOT,
        )

def test_materialize_semantic_release_candidate_accepts_row_cell_promotion_rule_source_path(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-row-path" / "release.json"
    precursor = _story_projection_precursor()
    precursor["promotion_rules"] = [{"slot": "narrator_voice", "source_paths": ["content.rows[*].narration_text"]}]

    result = dispatch(
        "materialize_semantic_release_candidate",
        _owner_request(
            "materialize_semantic_release_candidate",
            output_path=str(output_path),
            release_ref=_story_release_ref(),
            projection_update_state={
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [precursor],
            },
        ),
        project_root=MODULE_ROOT,
    )

    release = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert release["projections"][0]["promotion_rules"] == [
        {"slot": "narrator_voice", "source_paths": ["content.rows[*].narration_text"]}
    ]

def test_materialize_semantic_release_candidate_rejects_row_cells_wrapper_promotion_rule_source_path(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-row-cells-wrapper" / "release.json"
    precursor = _story_projection_precursor()
    precursor["promotion_rules"] = [{"slot": "narrator_voice", "source_paths": ["content.rows[*].cells.narration_text"]}]

    with pytest.raises(ValueError, match="Source Path"):
        dispatch(
            "materialize_semantic_release_candidate",
            _owner_request(
                "materialize_semantic_release_candidate",
                output_path=str(output_path),
                release_ref=_story_release_ref(),
                projection_update_state={
                    "schema_version": "kernel.create_projections_update_state.input.v1",
                    "projection_precursors": [precursor],
                },
            ),
            project_root=MODULE_ROOT,
        )

def test_materialize_semantic_release_candidate_rejects_promotion_rule_outside_projection_fields(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-outside-field" / "release.json"
    precursor = _story_projection_precursor()
    precursor["include_field_codes"] = ["story_title", "primary_setting", "fantasy_element", "other"]
    precursor["promotion_rules"] = [{"slot": "narrator_voice", "source_paths": ["content.fields.narrator_voice"]}]

    with pytest.raises(ValueError, match="nicht inkludierten Field Code"):
        dispatch(
            "materialize_semantic_release_candidate",
            _owner_request(
                "materialize_semantic_release_candidate",
                output_path=str(output_path),
                release_ref=_story_release_ref(),
                projection_update_state={
                    "schema_version": "kernel.create_projections_update_state.input.v1",
                    "projection_precursors": [precursor],
                },
            ),
            project_root=MODULE_ROOT,
        )
