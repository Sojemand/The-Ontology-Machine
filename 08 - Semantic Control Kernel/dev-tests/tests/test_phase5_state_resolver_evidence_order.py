from __future__ import annotations

from datetime import datetime, timezone

from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, StateEvidenceRef, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver import KernelStateResolver


NOW = datetime(2026, 5, 5, tzinfo=timezone.utc)


def test_kernel_binding_truth_wins_and_conflicting_owner_evidence_blocks() -> None:
    bundle = _bundle(
        _ref(
            "bind",
            "kernel_store_binding",
            "database_artifact_binding",
            {
                "database_id": "db_1",
                "database_path": "C:/db/main.sqlite",
                "artifact_root_path": "C:/artifact/kernel",
            },
        ),
        _ref(
            "owner_tree",
            "artifact_tree_folder_contract",
            "artifact_tree_folder_contract",
            {"exists": True, "artifact_root_path": "C:/artifact/owner"},
        ),
        _ref("db", "database_content_summary", "database_content_summary", {"database_exists": True, "record_count": 0}),
    )

    state = KernelStateResolver().resolve(
        TargetSelector.from_dict({"database_path": "C:/db/main.sqlite", "selected_existing_database": True}),
        bundle,
        NOW,
    )

    assert state.payload["artifact_tree"]["artifact_root_path"] == "C:/artifact/kernel"
    assert state.payload["blocking_reasons"][0]["blocker_code"] == "owner_evidence_conflict"


def test_false_friend_sources_cannot_become_resolver_truth() -> None:
    bundle = _bundle(
        _ref("db", "database_content_summary", "database_content_summary", {"database_exists": True, "record_count": 0}),
        _ref(
            "old",
            "inspect_active_corpus",
            "pipeline_active_release",
            {
                "exists": True,
                "complete": True,
                "release_fingerprint": "active-from-old-context",
                "taxonomy_fingerprint": "tax",
                "projection_count": 1,
            },
        ),
    )

    state = KernelStateResolver().resolve(TargetSelector.from_dict({"database_path": "C:/db/main.sqlite"}), bundle, NOW)

    assert state.payload["semantic_release_state"] == "no_semantic_release"
    assert "old" not in state.payload["evidence_refs"]


def test_pending_confirmation_and_interaction_refs_are_carried_from_resume_and_pending_confirmation_evidence() -> None:
    bundle = _bundle(
        _ref("db", "database_content_summary", "database_content_summary", {"database_exists": True, "record_count": 0}),
        _ref(
            "resume",
            "kernel_store_resume_state",
            "workflow_resume_state",
            {
                "workflow_run_id": "wrf_1",
                "pending_confirmation_refs": [{"confirmation_request_id": "cfq_resume"}],
                "pending_interaction_refs": [{"interaction_request_id": "int_resume"}],
            },
        ),
        _ref(
            "pending",
            "kernel_store_pending_confirmations",
            "pending_confirmation_record",
            {
                "workflow_run_id": "wrf_2",
                "confirmation_request": {
                    "confirmation_request_id": "cfq_pending",
                    "workflow_run_id": "wrf_2",
                },
            },
        ),
    )

    state = KernelStateResolver().resolve(TargetSelector.from_dict({"database_path": "C:/db/main.sqlite"}), bundle, NOW)

    assert state.payload["pending_confirmation_refs"] == [
        {"confirmation_request_id": "cfq_resume"},
        {"confirmation_request_id": "cfq_pending", "workflow_run_id": "wrf_2"},
    ]
    assert state.payload["pending_interaction_refs"] == [{"interaction_request_id": "int_resume"}]


def test_unrelated_lock_evidence_does_not_block_the_selected_target() -> None:
    bundle = _bundle(
        _ref("db", "database_content_summary", "database_content_summary", {"database_exists": True, "record_count": 0}),
        _ref(
            "other_lock",
            "kernel_store_locks",
            "lock_state",
            {"lock_id": "lock_other", "lock_type": "active_run", "status": "active"},
            target_identity={
                "schema_version": "state.target_identity.v1",
                "database_path_hash": "db_other",
                "artifact_root_path_hash": "",
                "lock_scope": "database",
                "target_hash": "tgt_other",
                "created_from": "fixture",
            },
        ),
    )

    state = KernelStateResolver().resolve(TargetSelector.from_dict({"database_path": "C:/db/main.sqlite"}), bundle, NOW)

    assert state.payload["active_lock_refs"] == []
    assert state.payload["blocking_reasons"] == []


def test_partially_matching_target_identity_does_not_make_lock_evidence_match() -> None:
    selector = TargetSelector.from_dict(
        {
            "database_path_hash": "dbhash",
            "artifact_root_path_hash": "arthash",
            "target_hash": "tgt_selected",
        }
    )
    bundle = StateEvidenceBundle(
        "bundle_partial_lock",
        "2026-05-05T00:00:00Z",
        selector,
        (
            _ref(
                "partial_lock",
                "kernel_store_locks",
                "lock_state",
                {"lock_id": "lock_partial", "lock_type": "active_run", "status": "active"},
                target_identity={
                    "schema_version": "state.target_identity.v1",
                    "database_path_hash": "dbhash",
                    "artifact_root_path_hash": "other_arthash",
                    "lock_scope": "database",
                    "target_hash": "tgt_other",
                    "created_from": "fixture",
                },
            ),
        ),
    )

    state = KernelStateResolver().resolve(selector, bundle, NOW)

    assert state.payload["active_lock_refs"] == []
    assert state.payload["blocking_reasons"] == []


def _bundle(*refs: StateEvidenceRef) -> StateEvidenceBundle:
    return StateEvidenceBundle(
        evidence_bundle_id="bundle_1",
        created_at="2026-05-05T00:00:00Z",
        target_selector=TargetSelector.from_dict({"database_path": "C:/db/main.sqlite"}),
        evidence_refs=refs,
    )


def _ref(
    ref_id: str,
    source: str,
    kind: str,
    payload: dict[str, object],
    *,
    target_identity: dict[str, object] | None = None,
) -> StateEvidenceRef:
    return StateEvidenceRef(
        evidence_ref_id=ref_id,
        source=source,
        kind=kind,
        target_identity=target_identity or {},
        payload_ref=payload,
        observed_at="2026-05-05T00:00:00Z",
        trust_class="test_fixture_evidence",
    )
