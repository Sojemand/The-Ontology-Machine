from __future__ import annotations

from pathlib import Path

import pytest

from normalizer_vision.assets import build_projection_catalog
from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets, validate_runtime_semantic_assets
from normalizer_vision.semantic_release import build_semantic_release


def test_build_runtime_semantic_assets_compiles_catalog_and_bundle(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    ocr_defaults = runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]

    assert runtime_assets["schema_version"] == "runtime_semantic_assets_v1"
    assert runtime_assets["release_fingerprint"] == release["fingerprint"]
    assert runtime_assets["projection_catalog"]["release_fingerprint"] == release["fingerprint"]
    assert runtime_assets["vision_policy_bundle"]["release_fingerprint"] == release["fingerprint"]
    assert runtime_assets["vision_policy_bundle"]["bundle_version"] == "vision_policy_bundle_v1"
    assert runtime_assets["vision_policy_bundle"]["ocr_policy"]["source_mode"] == "release_domain_merge"
    assert runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["profile_id"] == "layout_fidelity_v1"
    assert runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["render"]["page_image_dpi"] == 150
    assert "projection_overrides" not in runtime_assets["vision_policy_bundle"]["ocr_policy"]
    assert ocr_defaults["ocr_plugin"] == {"preferred_plugin": "optimizer-llm-ocr", "force_backup_on_scan": True}
    assert "paddlevl" not in ocr_defaults
    assert "device_policy" not in ocr_defaults
    semantic_policy = runtime_assets["vision_policy_bundle"]["semantic_extraction_policy"]
    assert semantic_policy["source_mode"] == "release_projection_compile"
    assert semantic_policy["policy_version"] == "semantic_extraction_policy_v2"
    assert semantic_policy["defaults"]["fallback_projection_id"] == "housing.default.v1"
    assert semantic_policy["defaults"]["default_profile"]["projection_id"] == "housing.default.v1"
    assert semantic_policy["defaults"]["default_profile"]["signals"]["text_markers"]
    assert semantic_policy["defaults"]["default_profile"]["signals"]["domain_markers"]["property"]
    assert semantic_policy["defaults"]["default_profile"]["signals"]["section_roles"]
    assert semantic_policy["defaults"]["default_profile"]["signals"]["party_roles"]
    assert semantic_policy["projection_overrides"]["finance.default.v1"]["rescue_families"] == {
        "document_header": True,
        "invoice_financial": True,
        "payment": True,
    }
    assert semantic_policy["projection_overrides"]["legal.public_admin.default.v1"]["rescue_families"] == {
        "document_header": True,
        "invoice_financial": False,
        "payment": False,
    }


def test_build_runtime_semantic_assets_catalog_version_is_deterministic(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    first = build_runtime_semantic_assets(release).to_dict()
    second = build_runtime_semantic_assets(release).to_dict()

    assert first["projection_catalog"]["catalog_version"] == second["projection_catalog"]["catalog_version"]


def test_direct_projection_catalog_matches_runtime_bundle_catalog(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    direct_catalog = build_projection_catalog(tmp_project_root).to_dict()
    runtime_catalog = build_runtime_semantic_assets(release).to_dict()["projection_catalog"]

    assert direct_catalog == runtime_catalog


def test_projection_catalog_preserves_release_projection_order(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    runtime_catalog = build_runtime_semantic_assets(release).to_dict()["projection_catalog"]

    assert [entry["projection_id"] for entry in runtime_catalog["projections"]] == release["projection_ids"]


def test_build_runtime_semantic_assets_rejects_missing_routing(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    broken_release = {**release, "projections": [dict(release["projections"][0])]}
    broken_release["projections"][0].pop("routing", None)

    with pytest.raises(ValueError, match="routing muss ein JSON-Objekt sein"):
        build_runtime_semantic_assets(broken_release)


def test_build_runtime_semantic_assets_rejects_missing_surface_signals(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    broken_release = {**release, "projections": [dict(release["projections"][0])]}
    broken_release["projections"][0]["routing"] = dict(broken_release["projections"][0]["routing"])
    broken_release["projections"][0]["routing"].pop("surface_signals", None)

    with pytest.raises(ValueError, match="surface_signals"):
        build_runtime_semantic_assets(broken_release)


def test_build_runtime_semantic_assets_rejects_unknown_domain_marker_key(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    broken_release = {**release, "projections": [dict(release["projections"][0])]}
    broken_release["projections"][0]["routing"] = dict(broken_release["projections"][0]["routing"])
    broken_release["projections"][0]["routing"]["surface_signals"] = dict(
        broken_release["projections"][0]["routing"]["surface_signals"]
    )
    broken_release["projections"][0]["routing"]["surface_signals"]["domain_markers"] = {
        **broken_release["projections"][0]["routing"]["surface_signals"]["domain_markers"],
        "broken_domain": ["marker"],
    }

    with pytest.raises(ValueError, match="unbekannte Keys"):
        build_runtime_semantic_assets(broken_release)


def test_build_runtime_semantic_assets_uses_balanced_ocr_profile_without_layout_domains(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    legal_only = {
        **release,
        "projections": [projection for projection in release["projections"] if projection.get("projection_id") == "legal.public_admin.default.v1"],
        "projection_ids": ["legal.public_admin.default.v1"],
    }

    runtime_assets = build_runtime_semantic_assets(legal_only).to_dict()

    assert runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["profile_id"] == "balanced_text_v1"
    assert runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["render"]["page_image_dpi"] == 150


def test_build_runtime_semantic_assets_rejects_invalid_ocr_profile_id(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["profile_id"] = "broken_profile"

    with pytest.raises(ValueError, match="profile_id"):
        validate_runtime_semantic_assets(runtime_assets)


def test_build_runtime_semantic_assets_rejects_invalid_semantic_budget(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    runtime_assets["vision_policy_bundle"]["semantic_extraction_policy"]["defaults"]["default_profile"]["budgets"].pop("max_facts")

    with pytest.raises(ValueError, match="max_facts"):
        validate_runtime_semantic_assets(runtime_assets)


def test_build_runtime_semantic_assets_rejects_local_ocr_runtime_leftovers(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["paddlevl"] = {"pipeline_version": "v1.5"}

    with pytest.raises(ValueError, match="lokale OCR-Altlasten"):
        validate_runtime_semantic_assets(runtime_assets)


def test_build_runtime_semantic_assets_rejects_local_ocr_plugin(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    runtime_assets["vision_policy_bundle"]["ocr_policy"]["defaults"]["ocr_plugin"]["preferred_plugin"] = "ocr-paddleocr-gpu"

    with pytest.raises(ValueError, match="optimizer-llm-ocr"):
        validate_runtime_semantic_assets(runtime_assets)
