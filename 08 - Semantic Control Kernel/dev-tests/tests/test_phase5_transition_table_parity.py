from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.domain.state_machine.models import ConfirmationGate
from semantic_control_kernel.domain.state_machine.transition_table import (
    TRANSITION_RULES,
    TRANSITION_RULE_BY_FUNCTION,
    parse_spec_02_transition_rows,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
SPEC_02 = PIPELINE_ROOT / "Semantic Kernel SPEC" / "02_kernel_state_transition_table.md"


def test_phase5_drift_preflight_records_build_plan_authority() -> None:
    payload = json.loads(
        (MODULE_ROOT / "dev-tests" / "fixtures" / "state_machine" / "phase5_drift_preflight.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["drift_preflight"] == "build_plan_authority_applied"
    assert payload["authority_notes"]


def test_transition_table_matches_spec_02_function_route_rows() -> None:
    rows = parse_spec_02_transition_rows(SPEC_02.read_text(encoding="utf-8"))

    assert len(rows) == 30
    assert len(TRANSITION_RULES) == 30
    for index, row in enumerate(rows, start=1):
        rule = TRANSITION_RULE_BY_FUNCTION[row["function_or_route"]]
        assert rule.rule_id == f"tr_{index:03d}"
        assert rule.required_state_text == row["required_state_text"]
        assert tuple(rule.required_inputs) == _required_inputs_from_spec(row["required_inputs_text"])
        assert rule.writes_or_mutates == row["writes_or_mutates"]
        assert rule.post_state_text == row["post_state_text"]
        assert _confirmation_represented(row["confirmation_text"], rule.confirmation_gate, rule.function_or_route)


def test_transition_table_has_stable_rule_ids_and_unique_routes() -> None:
    assert [rule.rule_id for rule in TRANSITION_RULES] == [f"tr_{index:03d}" for index in range(1, 31)]
    assert len({rule.function_or_route for rule in TRANSITION_RULES}) == 30


def _confirmation_represented(spec_text: str, gate: str, function_or_route: str) -> bool:
    text = spec_text.strip().casefold()
    if text == "no":
        return gate == ConfirmationGate.NONE.value
    if text == "yes when destructive":
        return gate == ConfirmationGate.DESTRUCTIVE_WHEN_PROJECTION_REMOVAL.value
    if text == "required by workflow when filled database path":
        return gate == ConfirmationGate.REQUIRED_BY_WORKFLOW_WHEN_FILLED_DATABASE_PATH.value
    if text == "user_type_decision_taxonomy":
        return gate == ConfirmationGate.USER_TYPE_DECISION_TAXONOMY.value
    if text == "user_type_decision_projections":
        return gate == ConfirmationGate.USER_TYPE_DECISION_PROJECTIONS.value
    if text == "user choice":
        return gate == ConfirmationGate.USER_CHOICE.value
    if text == "yes if overwrite":
        return gate == ConfirmationGate.OVERWRITE_ONLY.value
    if function_or_route == "pipeline_run":
        return gate == ConfirmationGate.INPUT_PRESENCE_CONFIRMATION.value
    return text == "yes" and gate == ConfirmationGate.DESTRUCTIVE.value


def _required_inputs_from_spec(spec_text: str) -> tuple[str, ...]:
    if spec_text in {"none", "deprecated alias candidate only"}:
        return ()
    return (spec_text,)
