from __future__ import annotations

import json

from .kernel_release_materialization_support import (
    MODULE_ROOT,
    _base_release_payload,
    _custom_taxonomy_ref,
    _owner_request,
    _projection_precursor,
    _runtime_profile_fingerprint,
    _story_projection_precursor,
    dispatch,
)

def test_materialize_semantic_release_candidate_writes_runtime_ready_custom_release(tmp_path: Path) -> None:
    base_release_path = tmp_path / "base" / "release.json"
    output_path = tmp_path / "custom" / "release.json"
    base_release_path.parent.mkdir(parents=True, exist_ok=True)
    base_release = _base_release_payload()
    base_release["release_version"] = "phase19.candidate"
    base_release_path.write_text(json.dumps(base_release), encoding="utf-8")

    result = dispatch(
        "materialize_semantic_release_candidate",
        _owner_request(
            "materialize_semantic_release_candidate",
            base_release_path=str(base_release_path),
            output_path=str(output_path),
            release_ref={
                "release_id": "custom.receipts.release",
                "release_fingerprint": "candidate-fingerprint",
                "taxonomy_ref": {"taxonomy_id": "normalizer_taxonomy.master", "taxonomy_fingerprint": "tax-fp", "runtime_locale": "en"},
                "projection_refs": [{"projection_id": "finance.receipts.v1", "projection_fingerprint": "proj-fp", "included_taxonomy_codes": ["invoice", "amount_due", "other"]}],
                "runtime_locale": "en",
            },
            projection_update_state={
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [_projection_precursor()],
            },
        ),
        project_root=MODULE_ROOT,
    )

    release = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert result["output_refs"]["release_ref"]["release_fingerprint"].startswith("sha256:")
    assert result["output_refs"]["release_ref"]["release_fingerprint"] != "candidate-fingerprint"
    assert release["release_id"] == "custom.receipts.release"
    assert release["release_version"] == "custom.v1"
    assert release["release_fingerprint"] == release["fingerprint"]
    assert release["projection_ids"] == ["finance.receipts.v1"]
    assert release["projections"][0]["projection_version"] == "v1"
    assert release["projections"][0]["include_field_codes"] == ["amount_due", "other"]
    assert _runtime_profile_fingerprint(release) == release["projections"][0]["projection_fingerprint"]
    assert release["projection_catalog"]["release_fingerprint"] == release["fingerprint"]
    assert release["runtime_semantic_assets"]["release_fingerprint"] == release["fingerprint"]
    assert release["runtime_semantic_assets"]["projection_catalog"]["release_fingerprint"] == release["fingerprint"]
    assert "phase19" not in json.dumps(release)
    assert "projection_overrides" not in release["runtime_semantic_assets"]["vision_policy_bundle"]["ocr_policy"]
    ocr_defaults = release["runtime_semantic_assets"]["vision_policy_bundle"]["ocr_policy"]["defaults"]
    assert ocr_defaults["ocr_plugin"]["preferred_plugin"] == "optimizer-llm-ocr"
    assert "paddlevl" not in ocr_defaults
    assert "device_policy" not in ocr_defaults

def test_materialize_semantic_release_candidate_accepts_full_custom_taxonomy_without_base_release(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-only" / "release.json"
    result = dispatch(
        "materialize_semantic_release_candidate",
        _owner_request(
            "materialize_semantic_release_candidate",
            output_path=str(output_path),
            release_ref={
                "release_id": "custom.story.release",
                "release_version": "custom.v1",
                "release_fingerprint": "candidate-fingerprint",
                "taxonomy_ref": _custom_taxonomy_ref(),
                "projection_refs": [
                    {
                        "projection_id": "creative_writing.short_story_text.v1",
                        "projection_fingerprint": "proj-story-fp",
                        "included_taxonomy_codes": ["short_story", "story_title", "primary_setting", "fantasy_element", "narrator_voice", "story_paragraph", "narration_text", "other"],
                    }
                ],
                "runtime_locale": "en",
            },
            projection_update_state={
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [_story_projection_precursor()],
            },
        ),
        project_root=MODULE_ROOT,
    )

    release = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert release["release_id"] == "custom.story.release"
    assert release["master_taxonomy_id"] == "custom.story.taxonomy"
    assert release["master_taxonomy_version"] == "custom.v1"
    assert [item["code"] for item in release["master_taxonomy"]["entity_types"]] == ["document_fact"]
    assert [item["code"] for item in release["master_taxonomy"]["role_types"]] == ["story_paragraph", "other"]
    assert "relation_types" not in release["master_taxonomy"]
    assert not {"party", "financial_amount", "property", "measurement"}.intersection(
        {item["code"] for item in release["master_taxonomy"]["entity_types"]}
    )
    assert not {"issuer", "tenant", "property_manager", "measurement_entry", "timeline_entry"}.intersection(
        {item["code"] for item in release["master_taxonomy"]["role_types"]}
    )
    assert "Adresse oder ortsbezogene Anschrift" not in json.dumps(release["master_taxonomy"], ensure_ascii=False)
    assert release["master_taxonomy"]["field_codes"][0]["label"] == "Story title"
    assert [slot["slot"] for slot in release["master_taxonomy"]["promotion_slots"]] == [
        "story_title",
        "primary_setting",
        "fantasy_element",
        "narrator_voice",
    ]
    assert release["projection_ids"] == ["creative_writing.short_story_text.v1"]
    assert release["projections"][0]["promotion_rules"] == [
        {"slot": "story_title", "source_paths": ["content.fields.story_title"]},
        {"slot": "primary_setting", "source_paths": ["content.fields.primary_setting"]},
        {"slot": "fantasy_element", "source_paths": ["content.fields.fantasy_element"]},
        {"slot": "narrator_voice", "source_paths": ["content.fields.narrator_voice"]},
    ]
    assert release["release_fingerprint"] == release["fingerprint"]
    assert _runtime_profile_fingerprint(release) == release["projections"][0]["projection_fingerprint"]
    assert release["projections"][0]["projection_fingerprint"] != "proj-story-fp"
    assert release["projection_catalog"]["release_fingerprint"] == release["fingerprint"]
    assert release["runtime_semantic_assets"]["promotion_slots"] == release["master_taxonomy"]["promotion_slots"]
    assert release["runtime_semantic_assets"]["projection_catalog"]["projections"][0]["field_slot_map"]["primary_setting"] == "primary_setting"
    assert result["output_refs"]["release_ref"]["release_fingerprint"] == release["fingerprint"]
