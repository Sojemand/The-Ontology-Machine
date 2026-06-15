from __future__ import annotations

import pytest

from normalizer_vision.taxonomy_sources import load_source_package
from tests.fixtures.taxonomy_source_package import clone_locale, package_paths, read_yaml, write_yaml


def test_source_package_requires_all_mandatory_files(tmp_project_root):
    paths = package_paths(tmp_project_root)
    paths.master_core_path.unlink()

    with pytest.raises(ValueError, match="fehlend"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_text_fields_in_master_core(tmp_project_root):
    paths = package_paths(tmp_project_root)
    master_core = read_yaml(paths.master_core_path)
    master_core["categories"]["finance"]["label"] = "Finance"
    write_yaml(paths.master_core_path, master_core)

    with pytest.raises(ValueError, match="darf nicht im Core-Source liegen"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_routing_lexicon_in_projection_core(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.core_path)
    payload["routing_lexicon"] = {"text_markers": ["rechnung"], "domain_markers": {"finance": ["rechnung"]}}
    write_yaml(projection.core_path, payload)

    with pytest.raises(ValueError, match="unbekannte Felder"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_projection_id_in_text_file(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.text_path)
    payload["projection_id"] = projection.projection_id
    write_yaml(projection.text_path, payload)

    with pytest.raises(ValueError, match="unbekannte Felder"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_core_lists_in_text_file(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.text_path)
    payload["include_document_types"] = ["invoice"]
    write_yaml(projection.text_path, payload)

    with pytest.raises(ValueError, match="unbekannte Felder"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_alias_collisions(tmp_project_root):
    paths = package_paths(tmp_project_root)
    master_text = read_yaml(paths.master_text_path)
    master_text["categories"]["legal"]["aliases"] = ["finance"]
    write_yaml(paths.master_text_path, master_text)

    with pytest.raises(ValueError, match="Alias-Kollisionen"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_unknown_projection_include_code(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.core_path)
    payload["include_document_types"].append("missing_document_type")
    write_yaml(projection.core_path, payload)

    with pytest.raises(ValueError, match="referenziert unbekannte Werte"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_empty_routing_lexicon(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.text_path)
    payload["routing_lexicon"]["text_markers"] = []
    payload["routing_lexicon"]["domain_markers"] = {}
    write_yaml(projection.text_path, payload)

    with pytest.raises(ValueError, match="routing_lexicon darf nicht leer sein"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_invalid_section_role(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.core_path)
    payload["routing"]["section_roles"] = ["bad role"]
    write_yaml(projection.core_path, payload)

    with pytest.raises(ValueError, match="section_roles"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_invalid_party_role_key(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.core_path)
    payload["routing"]["party_roles"] = ["bad role"]
    write_yaml(projection.core_path, payload)

    with pytest.raises(ValueError, match="Rollen-Keys"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_invalid_semantic_binding_target(tmp_project_root):
    paths = package_paths(tmp_project_root)
    master_core = read_yaml(paths.master_core_path)
    master_core["field_codes"]["issuer"]["promotion_slot"] = "broken_slot"
    write_yaml(paths.master_core_path, master_core)

    with pytest.raises(ValueError, match="promotion_slot"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_invalid_value_type(tmp_project_root):
    paths = package_paths(tmp_project_root)
    master_core = read_yaml(paths.master_core_path)
    master_core["field_codes"]["issuer"]["value_type"] = "money"
    write_yaml(paths.master_core_path, master_core)

    with pytest.raises(ValueError, match="value_type"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_projection_without_meaningful_coverage(tmp_project_root):
    projection = package_paths(tmp_project_root).projections[0]
    payload = read_yaml(projection.core_path)
    payload["include_document_types"] = []
    payload["routing"]["example_document_types"] = []
    write_yaml(projection.core_path, payload)

    with pytest.raises(ValueError, match="Fachabdeckung"):
        load_source_package(tmp_project_root)


def test_source_package_requires_locale_text_files_for_all_declared_locales(tmp_project_root):
    paths = package_paths(tmp_project_root)
    paths.projections[0].text_path_for("en").unlink()

    with pytest.raises(ValueError, match="fehlend"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_default_locale_outside_available_locales(tmp_project_root):
    paths = package_paths(tmp_project_root)
    release = read_yaml(paths.release_path)
    release["default_authoring_locale"] = "fr"
    write_yaml(paths.release_path, release)

    with pytest.raises(ValueError, match="default_authoring_locale"):
        load_source_package(tmp_project_root)


def test_source_package_rejects_missing_optional_glossary_for_new_locale(tmp_project_root):
    with pytest.raises(ValueError, match="en-only"):
        clone_locale(tmp_project_root, target_locale="fr", include_glossary=False)
