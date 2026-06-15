from __future__ import annotations

import shutil

import pytest

from normalizer_vision.assets.workflow import build_projection_catalog
from normalizer_vision.taxonomy_sources.adapter import discover_relative_files
from normalizer_vision.taxonomy_sources import load_source_package
from tests.fixtures.taxonomy_source_package import clone_locale, package_paths, read_yaml, write_yaml


def test_source_package_exists_with_exact_blanket_file_set(tmp_project_root):
    paths = package_paths(tmp_project_root)
    package = load_source_package(tmp_project_root)

    assert paths.root.exists()
    assert len(paths.relative_files()) == 25
    assert set(discover_relative_files(paths.root)) == set(paths.relative_files())
    assert package["release"]["release_id"] == "semantic_release.default"
    assert package["release"]["governance"]["source_package_blanket_exception"]["allowed_file_count"] == len(paths.relative_files())


def test_source_package_governance_matches_projection_recipe(tmp_project_root):
    paths = package_paths(tmp_project_root)
    release = read_yaml(paths.release_path)

    assert release["projection_ids"] == [projection.projection_id for projection in paths.projections]
    assert release["available_locales"] == ["en"]
    assert release["default_authoring_locale"] == "en"
    assert release["default_runtime_locale"] == "en"
    assert release["governance"]["source_package_blanket_exception"]["kind"] == "locale_aware_source_package"
    assert release["governance"]["source_package_blanket_exception"]["projection_count"] == len(paths.projections)
    assert release["governance"]["source_package_blanket_exception"]["files"] == list(paths.relative_files())


def test_default_source_package_defines_dynamic_promotion_surface(tmp_project_root):
    package = load_source_package(tmp_project_root)
    master_core = package["master"]["core"]
    slots = {
        str(item.get("slot") or "").strip()
        for item in master_core["promotion_slots"]
        if isinstance(item, dict)
    }

    assert slots
    assert {"document_title", "primary_party", "document_identifier"} <= slots
    for projection_id, projection in package["projections"].items():
        rules = projection["core"]["promotion_rules"]
        assert rules, projection_id
        assert {
            str(rule.get("slot") or "").strip()
            for rule in rules
            if isinstance(rule, dict)
        } <= slots
        assert all(rule.get("source_paths") for rule in rules)


def test_source_package_loader_does_not_fallback_to_flat_assets(tmp_project_root):
    shutil.rmtree(package_paths(tmp_project_root).root)

    with pytest.raises(ValueError, match="Source-Paket fehlt"):
        load_source_package(tmp_project_root)


def test_source_authoritative_catalog_fails_if_source_package_is_invalid(tmp_project_root):
    release = read_yaml(package_paths(tmp_project_root).release_path)
    release["default_runtime_locale"] = "fr"
    write_yaml(package_paths(tmp_project_root).release_path, release)

    with pytest.raises(ValueError, match="default_runtime_locale"):
        load_source_package(tmp_project_root)

    with pytest.raises(ValueError, match="default_runtime_locale"):
        build_projection_catalog(tmp_project_root)


def test_catalog_ignores_corrupted_flat_projection_compatibility_files(tmp_project_root):
    flat_path = tmp_project_root / "config" / "normalizer_taxonomy.finance.default.v1.json"
    flat_path.write_text("{broken", encoding="utf-8")

    catalog = build_projection_catalog(tmp_project_root)

    assert catalog.master_taxonomy_version == "2026-03-28.v6"
    assert flat_path.read_text(encoding="utf-8") == "{broken"


def test_source_package_rejects_extra_file_outside_blanket_allowlist(tmp_project_root):
    paths = package_paths(tmp_project_root)
    extra_path = paths.root / "projections" / "finance.default.v1.text.fr.yaml"
    extra_path.write_text("label: Finance\n", encoding="utf-8")

    with pytest.raises(ValueError, match="extra"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_new_locale_without_code_changes(tmp_project_root):
    with pytest.raises(ValueError, match="en-only"):
        clone_locale(tmp_project_root, target_locale="fr")
