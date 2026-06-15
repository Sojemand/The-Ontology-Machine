from __future__ import annotations

from datetime import datetime, timezone

from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, StateEvidenceRef, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver import KernelStateResolver


NOW = datetime(2026, 5, 5, tzinfo=timezone.utc)
SELECTOR = TargetSelector.from_dict({"database_path": "C:/db/main.sqlite"})


def test_release_state_precedence_separates_no_incomplete_attached_and_active() -> None:
    assert _resolve(_bundle(_db())).payload["semantic_release_state"] == "no_semantic_release"
    assert _resolve(_bundle(_db(), _ref("staged", "staged_semantic_release", {"exists": True}))).payload[
        "semantic_release_state"
    ] == "semantic_release_incomplete"
    assert _resolve(_bundle(_db(), _attach("fp_1"))).payload["semantic_release_state"] == "semantic_release_complete_not_active"
    assert _resolve(_bundle(_db(), _active("fp_1"))).payload["semantic_release_state"] == "semantic_release_active"


def test_conflicting_attach_and_active_fingerprints_block_as_target_identity_changed() -> None:
    state = _resolve(_bundle(_db(), _attach("fp_attached"), _active("fp_active")))

    assert state.payload["semantic_release_state"] == "unknown"
    assert state.payload["blocking_reasons"][0]["blocker_code"] == "target_identity_changed"


def test_complete_flag_without_taxonomy_and_projection_proof_is_incomplete() -> None:
    state = _resolve(
        _bundle(
            _db(),
            _ref(
                "active_incomplete",
                "pipeline_active_release",
                {
                    "exists": True,
                    "complete": True,
                    "release_fingerprint": "fp_active",
                },
            ),
        )
    )

    assert state.payload["semantic_release_state"] == "semantic_release_incomplete"
    assert state.payload["blocking_reasons"][0]["blocker_code"] == "release_incomplete"


def _resolve(bundle: StateEvidenceBundle):
    return KernelStateResolver().resolve(SELECTOR, bundle, NOW)


def _bundle(*refs: StateEvidenceRef) -> StateEvidenceBundle:
    return StateEvidenceBundle("bundle", "2026-05-05T00:00:00Z", SELECTOR, refs)


def _db() -> StateEvidenceRef:
    return _ref("db", "database_content_summary", {"database_exists": True, "record_count": 0})


def _attach(fingerprint: str) -> StateEvidenceRef:
    return _ref(
        "attach",
        "semantic_release_attach_state",
        {
            "release_id": "rel",
            "release_version": "1",
            "release_fingerprint": fingerprint,
            "taxonomy_fingerprint": "tax",
            "projection_count": 1,
            "written_release_exists": True,
        },
        source="kernel_store_attach_state",
    )


def _active(fingerprint: str) -> StateEvidenceRef:
    return _ref(
        "active",
        "pipeline_active_release",
        {
            "exists": True,
            "release_id": "rel",
            "release_version": "1",
            "release_fingerprint": fingerprint,
            "taxonomy_fingerprint": "tax",
            "projection_count": 1,
        },
    )


def _ref(ref_id: str, kind: str, payload: dict[str, object], *, source: str | None = None) -> StateEvidenceRef:
    return StateEvidenceRef(ref_id, source or kind, kind, {}, payload, "2026-05-05T00:00:00Z", "test_fixture_evidence")
