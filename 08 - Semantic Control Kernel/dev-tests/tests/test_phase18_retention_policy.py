from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from semantic_control_kernel.debug.retention import SupportBundleRetentionPolicy
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore


def test_retention_plan_and_apply_prune_preserve_non_bundle_truth(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = SupportBundleStore(paths)
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "retention_target"},
        "phase18_retention_test",
    )

    stale_ref = store.write_support_bundle(
        category="support_only_unrecoverable",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_retention",
        summary="Stale recovery bundle.",
        workflow_tool=run.workflow_tool,
        retention_class="stale_recovery_90_days",
    )
    manual_ref = store.write_support_bundle(
        category="final_error",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_retention_manual",
        summary="Manual retention bundle.",
        workflow_tool=run.workflow_tool,
        retention_class="final_error_manual",
    )

    stale_manifest = store.get_manifest(stale_ref.payload["support_bundle_id"])
    manual_manifest = store.get_manifest(manual_ref.payload["support_bundle_id"])
    assert stale_manifest["expires_at"]
    assert "expires_at" not in manual_manifest

    future = (datetime.now(timezone.utc) + timedelta(days=91)).isoformat().replace("+00:00", "Z")
    policy = SupportBundleRetentionPolicy(paths, store)
    plan = policy.plan_prune(future, dry_run=True)
    assert stale_ref.payload["support_bundle_id"] in plan.payload["expired_bundle_ids"]
    assert manual_ref.payload["support_bundle_id"] in plan.payload["retained_bundle_ids"]

    cleanup = policy.apply_prune(plan, "phase18 retention test")
    cleanup_path = paths.support_cleanup_history_dir / f"{cleanup['cleanup_id']}.json"
    assert cleanup_path.is_file()
    assert not (paths.support_bundles_dir / stale_ref.payload["support_bundle_id"]).exists()
    assert (paths.support_bundles_dir / manual_ref.payload["support_bundle_id"]).exists()
    assert not (paths.debug_redaction_reports_dir / f"{stale_ref.payload['support_bundle_id']}.json").exists()
    assert (paths.debug_redaction_reports_dir / f"{manual_ref.payload['support_bundle_id']}.json").exists()

    index_payload = json.loads(paths.support_index_path.read_text(encoding="utf-8"))
    assert [item["support_bundle_id"] for item in index_payload["support_bundle_refs"]] == [
        manual_ref.payload["support_bundle_id"]
    ]


def test_retention_apply_prune_requires_dry_run_evidence(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = SupportBundleStore(paths)
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "retention_guard"},
        "phase18_retention_guard",
    )
    ref = store.write_support_bundle(
        category="support_only_unrecoverable",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_guard",
        summary="Guard bundle.",
        workflow_tool=run.workflow_tool,
        retention_class="stale_recovery_90_days",
    )
    plan = SupportBundleRetentionPolicy(paths, store).plan_prune(
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        dry_run=False,
    )

    try:
        SupportBundleRetentionPolicy(paths, store).apply_prune(plan, "should fail")
    except ValueError as exc:
        assert "dry-run evidence" in str(exc)
    else:  # pragma: no cover - explicit regression guard
        raise AssertionError("apply_prune accepted a non-dry-run plan.")

    assert (paths.support_bundles_dir / ref.payload["support_bundle_id"]).exists()


def test_retention_apply_prune_rechecks_expiry_before_deleting(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = SupportBundleStore(paths)
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "retention_forged_plan"},
        "phase18_retention_forged_plan",
    )
    ref = store.write_support_bundle(
        category="final_error",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_forged",
        summary="Manual bundle must survive forged prune plans.",
        workflow_tool=run.workflow_tool,
        retention_class="final_error_manual",
    )
    forged_plan = {
        "schema_version": "debug.support_bundle_prune_plan.v1",
        "planned_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat().replace("+00:00", "Z"),
        "dry_run": True,
        "expired_bundle_ids": [ref.payload["support_bundle_id"]],
        "retained_bundle_ids": [],
    }

    cleanup = SupportBundleRetentionPolicy(paths, store).apply_prune(
        forged_plan,
        "phase18 forged plan regression",
    )

    assert cleanup["deleted_bundle_ids"] == []
    assert ref.payload["support_bundle_id"] in cleanup["retained_bundle_ids"]
    assert (paths.support_bundles_dir / ref.payload["support_bundle_id"]).exists()
