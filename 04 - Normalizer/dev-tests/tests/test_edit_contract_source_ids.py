from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tests.edit_contract_shared import _run_contract


def test_source_authoring_rejects_path_like_release_id_before_mutation(tmp_project_root: Path) -> None:
    response = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": "normalizer.semantic_release_authoring"})
    value = response["value"]
    value["release_id"] = r"..\escaped_release"

    written = _run_contract(
        tmp_project_root,
        {"action": "write_surface", "surface_id": "normalizer.semantic_release_authoring", "value": value},
    )

    assert written["status"] == "error"
    assert "release_id" in written["reason"]
    assert (tmp_project_root / "config" / "taxonomy_sources" / "semantic_release.default" / "release.yaml").exists()
    assert not (tmp_project_root / "config" / "escaped_release").exists()


def test_source_authoring_rejects_path_like_projection_id_before_yaml_write(tmp_project_root: Path) -> None:
    response = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": "normalizer.taxonomy_profiles"})
    value = response["value"]
    bad_projection_id = "../escaped_projection"
    projection = deepcopy(value["profiles"]["finance.default.v1"])
    projection["projection_id"] = bad_projection_id
    projection["core"]["projection_id"] = bad_projection_id
    value["profiles"] = {bad_projection_id: projection, **value["profiles"]}

    written = _run_contract(
        tmp_project_root,
        {"action": "write_surface", "surface_id": "normalizer.taxonomy_profiles", "value": value},
    )

    assert written["status"] == "error"
    assert "Source-ID" in written["reason"]
    source_root = tmp_project_root / "config" / "taxonomy_sources" / "semantic_release.default"
    assert (source_root / "projections" / "finance.default.v1.core.yaml").exists()
    assert not (source_root / "escaped_projection.core.yaml").exists()
