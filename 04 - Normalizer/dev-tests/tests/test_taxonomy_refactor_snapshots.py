from __future__ import annotations

import pytest

from tests.fixtures.taxonomy_refactor_baseline import (
    INVENTORY_CASES,
    comparable_snapshot_fingerprint,
    core_leaf_values,
    live_snapshot_payloads,
    load_fingerprint_manifest,
    load_provenance,
    load_snapshot_payload,
)


@pytest.fixture(scope="module")
def live_snapshots() -> dict[str, object]:
    return live_snapshot_payloads()


def test_frozen_head_baseline_provenance_is_recorded() -> None:
    provenance = load_provenance()

    assert provenance["source_ref"] == "HEAD"
    assert provenance["git_commit"]
    assert provenance["generated_at"]
    assert provenance["snapshot_root"] == "dev-tests/fixtures/taxonomy_refactor_baseline/frozen_head"


@pytest.mark.parametrize(
    ("artifact_kind", "snapshot_name", "projection_id"),
    INVENTORY_CASES,
    ids=[snapshot_name for _, snapshot_name, _ in INVENTORY_CASES],
)
def test_snapshot_core_payload_matches_frozen_baseline(
    live_snapshots,
    artifact_kind: str,
    snapshot_name: str,
    projection_id: str | None,
) -> None:
    assert core_leaf_values(
        live_snapshots[snapshot_name],
        artifact_kind=artifact_kind,
        projection_id=projection_id,
    ) == core_leaf_values(
        load_snapshot_payload(snapshot_name),
        artifact_kind=artifact_kind,
        projection_id=projection_id,
    )


def test_snapshot_fingerprint_manifest_matches_current_artifacts(live_snapshots):
    observed = {
        snapshot_name: comparable_snapshot_fingerprint(
            live_snapshots[snapshot_name],
            artifact_kind=artifact_kind,
            projection_id=projection_id,
        )
        for artifact_kind, snapshot_name, projection_id in INVENTORY_CASES
    }

    assert observed == load_fingerprint_manifest()
