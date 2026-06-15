from __future__ import annotations

import pytest

from tests.fixtures.taxonomy_refactor_baseline import (
    INVENTORY_CASES,
    VALID_CLASSIFICATIONS,
    build_inventory_entries,
    inventory_location_key_for,
    inventory_location_value_for,
    live_snapshot_payloads,
    load_inventory_entries,
)


@pytest.fixture(scope="module")
def live_snapshots() -> dict[str, object]:
    return live_snapshot_payloads()


@pytest.mark.parametrize(
    ("artifact_kind", "snapshot_name", "projection_id"),
    INVENTORY_CASES,
    ids=[snapshot_name for _, snapshot_name, _ in INVENTORY_CASES],
)
def test_inventory_matches_current_leaf_and_empty_paths(
    live_snapshots,
    artifact_kind: str,
    snapshot_name: str,
    projection_id: str | None,
):
    observed = build_inventory_entries(
        live_snapshots[snapshot_name],
        artifact_kind=artifact_kind,
        projection_id=projection_id,
    )
    expected = load_inventory_entries(snapshot_name)

    assert observed == expected


@pytest.mark.parametrize(
    ("artifact_kind", "snapshot_name", "projection_id"),
    INVENTORY_CASES,
    ids=[snapshot_name for _, snapshot_name, _ in INVENTORY_CASES],
)
def test_inventory_entries_are_unique_and_single_class(
    artifact_kind: str,
    snapshot_name: str,
    projection_id: str | None,
):
    entries = load_inventory_entries(snapshot_name)
    paths = [entry["json_path"] for entry in entries]

    assert len(paths) == len(set(paths))
    for entry in entries:
        assert entry["artifact_kind"] == artifact_kind
        assert entry["classification"] in VALID_CLASSIFICATIONS
        assert entry["value_kind"]
        location_key = inventory_location_key_for(artifact_kind)
        assert location_key in entry
        assert entry[location_key] == inventory_location_value_for(
            artifact_kind,
            entry["classification"],
            projection_id=projection_id,
        )
