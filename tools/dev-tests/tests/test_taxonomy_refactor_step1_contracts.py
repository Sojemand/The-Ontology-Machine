from __future__ import annotations

import pytest

from step1_contract_support import BASELINE, live_contract_snapshot_payloads

CONTRACT_SNAPSHOT_NAMES = tuple(snapshot_name for _, snapshot_name, _ in BASELINE.CONTRACT_INVENTORY_CASES)


@pytest.fixture(scope="module")
def live_contract_snapshots(tmp_path_factory) -> dict[str, object]:
    return live_contract_snapshot_payloads(tmp_path_factory.mktemp("step1-contract-chain"))


@pytest.mark.parametrize(
    ("artifact_kind", "snapshot_name", "projection_id"),
    BASELINE.CONTRACT_INVENTORY_CASES,
    ids=[snapshot_name for _, snapshot_name, _ in BASELINE.CONTRACT_INVENTORY_CASES],
)
def test_contract_snapshot_core_payload_matches_frozen_baseline(
    live_contract_snapshots,
    artifact_kind: str,
    snapshot_name: str,
    projection_id: str | None,
) -> None:
    assert BASELINE.core_leaf_values(
        live_contract_snapshots[snapshot_name],
        artifact_kind=artifact_kind,
        projection_id=projection_id,
    ) == BASELINE.core_leaf_values(
        BASELINE.load_contract_snapshot_payload(snapshot_name),
        artifact_kind=artifact_kind,
        projection_id=projection_id,
    )


def test_contract_snapshot_fingerprint_manifest_matches_current_chain(live_contract_snapshots) -> None:
    observed = {
        snapshot_name: BASELINE.comparable_snapshot_fingerprint(
            live_contract_snapshots[snapshot_name],
            artifact_kind=artifact_kind,
            projection_id=projection_id,
        )
        for artifact_kind, snapshot_name, projection_id in BASELINE.CONTRACT_INVENTORY_CASES
    }

    assert observed == BASELINE.load_contract_fingerprint_manifest()


@pytest.mark.parametrize(
    ("artifact_kind", "snapshot_name", "projection_id"),
    BASELINE.CONTRACT_INVENTORY_CASES,
    ids=[snapshot_name for _, snapshot_name, _ in BASELINE.CONTRACT_INVENTORY_CASES],
)
def test_contract_inventory_matches_current_chain(
    live_contract_snapshots,
    artifact_kind: str,
    snapshot_name: str,
    projection_id: str | None,
) -> None:
    observed = BASELINE.build_inventory_entries(
        live_contract_snapshots[snapshot_name],
        artifact_kind=artifact_kind,
        projection_id=projection_id,
    )
    expected = BASELINE.load_contract_inventory_entries(snapshot_name)

    assert observed == expected


@pytest.mark.parametrize(
    ("artifact_kind", "snapshot_name", "projection_id"),
    BASELINE.CONTRACT_INVENTORY_CASES,
    ids=[snapshot_name for _, snapshot_name, _ in BASELINE.CONTRACT_INVENTORY_CASES],
)
def test_contract_inventory_entries_are_unique_and_bucketed(
    artifact_kind: str,
    snapshot_name: str,
    projection_id: str | None,
) -> None:
    entries = BASELINE.load_contract_inventory_entries(snapshot_name)
    paths = [entry["json_path"] for entry in entries]

    assert len(paths) == len(set(paths))
    for entry in entries:
        assert entry["artifact_kind"] == artifact_kind
        assert entry["classification"] in BASELINE.VALID_CLASSIFICATIONS
        assert entry["value_kind"]
        assert entry["origin_bucket"] == BASELINE.inventory_location_value_for(
            artifact_kind,
            entry["classification"],
            projection_id=projection_id,
        )


def test_contract_inventory_keeps_projection_hint_and_projection_selection_reason(
    live_contract_snapshots,
) -> None:
    structured = live_contract_snapshots[BASELINE.STRUCTURED_SNAPSHOT_NAME]
    normalized = live_contract_snapshots[BASELINE.NORMALIZED_SNAPSHOT_NAME]
    structured_paths = {
        entry["json_path"] for entry in BASELINE.load_contract_inventory_entries(BASELINE.STRUCTURED_SNAPSHOT_NAME)
    }
    normalized_paths = {
        entry["json_path"] for entry in BASELINE.load_contract_inventory_entries(BASELINE.NORMALIZED_SNAPSHOT_NAME)
    }

    assert structured["context"]["projection_hint"]["projection_id"] == "finance.default.v1"
    assert structured["context"]["projection_hint"]["reason"]
    assert "$.context.projection_hint.projection_id" in structured_paths
    assert "$.context.projection_hint.reason" in structured_paths

    assert normalized["projection"]["selection"]["reason"]
    assert "$.projection.selection.reason" in normalized_paths
