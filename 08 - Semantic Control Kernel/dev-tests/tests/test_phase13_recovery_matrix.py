from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.domain.recovery.recovery_matrix import RecoveryMatrix
from semantic_control_kernel.types.enums import RecoveryStateClass


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_INVENTORY = MODULE_ROOT / "dev-tests" / "fixtures" / "phase13" / "fixture_inventory.json"


def test_drift_preflight_records_build_plan_authority() -> None:
    payload = json.loads(FIXTURE_INVENTORY.read_text(encoding="utf-8"))

    assert payload["drift_preflight"]["status"] == "drift_preflight: build_plan_authority_applied"
    assert payload["drift_preflight"]["details"]


def test_recovery_matrix_covers_every_phase2_recovery_state() -> None:
    matrix = RecoveryMatrix()

    matrix.assert_complete()
    assert set(matrix.entries) == set(RecoveryStateClass.values())


def test_every_recovery_state_has_required_phase13_rules() -> None:
    matrix = RecoveryMatrix()

    for state in RecoveryStateClass.values():
        entry = matrix.get(state)
        assert entry.detectors
        assert entry.blocked_functions
        assert entry.recovery_options
        assert entry.event_scoped_agent_tools
        assert entry.required_receipt
        assert entry.post_state
        assert entry.must_not


def test_fixture_inventory_lists_all_phase13_fixture_classes() -> None:
    payload = json.loads(FIXTURE_INVENTORY.read_text(encoding="utf-8"))

    assert len(payload["fixtures"]) == 21
    assert "support_only_unknown_exception" in payload["fixtures"]
    assert "superseded_mirror_event_tool_call" in payload["fixtures"]
