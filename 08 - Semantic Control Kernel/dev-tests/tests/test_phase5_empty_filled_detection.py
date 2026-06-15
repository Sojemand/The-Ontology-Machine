from __future__ import annotations

from datetime import datetime, timezone

from semantic_control_kernel.domain.state_machine.identity import build_target_identity
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, StateEvidenceRef, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver import KernelStateResolver


NOW = datetime(2026, 5, 5, tzinfo=timezone.utc)
SELECTOR = TargetSelector.from_dict({"database_path": "C:/db/main.sqlite"})


def test_resolver_detects_empty_and_filled_databases() -> None:
    empty = _resolve(_bundle(_ref("db_empty", "database_content_summary", {"database_exists": True, "record_count": 0})))
    filled = _resolve(_bundle(_ref("db_filled", "database_content_summary", {"database_exists": True, "record_count": 3})))

    assert empty.payload["database_emptiness"] == "empty"
    assert filled.payload["database_emptiness"] == "filled"


def test_conflicting_batch_evidence_makes_emptiness_unknown() -> None:
    state = _resolve(
        _bundle(
            _ref("db_empty", "database_content_summary", {"database_exists": True, "record_count": 0}),
            _ref("batch", "pipeline_batch_manifest", {"record_count": 2}),
        )
    )

    assert state.payload["database_emptiness"] == "unknown"
    assert state.payload["blocking_reasons"][0]["blocker_code"] == "owner_evidence_conflict"


def test_missing_database_count_evidence_makes_emptiness_unknown() -> None:
    state = _resolve(_bundle(_ref("db_unknown", "database_content_summary", {"database_exists": True})))

    assert state.payload["database_emptiness"] == "unknown"
    assert state.payload["blocking_reasons"][0]["blocker_code"] == "database_emptiness_unknown"


def test_owner_target_mismatch_makes_emptiness_unknown_even_with_record_count() -> None:
    state = _resolve(
        _bundle(
            _ref(
                "db_mismatch",
                "database_content_summary",
                {
                    "database_exists": True,
                    "record_count": 4,
                    "target_identity": build_target_identity({"database_path": "C:/db/other.sqlite"}).to_dict(),
                },
            )
        )
    )

    assert state.payload["database_emptiness"] == "unknown"
    assert state.payload["blocking_reasons"][0]["blocker_code"] == "owner_evidence_conflict"


def _resolve(bundle: StateEvidenceBundle):
    return KernelStateResolver().resolve(SELECTOR, bundle, NOW)


def _bundle(*refs: StateEvidenceRef) -> StateEvidenceBundle:
    return StateEvidenceBundle("bundle", "2026-05-05T00:00:00Z", SELECTOR, refs)


def _ref(ref_id: str, kind: str, payload: dict[str, object]) -> StateEvidenceRef:
    return StateEvidenceRef(ref_id, kind, kind, {}, payload, "2026-05-05T00:00:00Z", "test_fixture_evidence")
