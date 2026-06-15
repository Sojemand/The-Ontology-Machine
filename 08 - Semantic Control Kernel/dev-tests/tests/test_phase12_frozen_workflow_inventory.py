from __future__ import annotations

from semantic_control_kernel.workflows.merge.routes import route_sequence as merge_route_sequence
from phase12_frozen_inventory import FROZEN_OPERATIONAL_GOLDEN, REQUESTED_WORKFLOWS, _golden

def test_frozen_operational_workflow_inventory_matches_requested_scope() -> None:
    assert FROZEN_OPERATIONAL_GOLDEN["schema_version"] == "kernel.phase12.frozen_operational_workflows.v1"
    assert tuple(entry["workflow_tool"] for entry in FROZEN_OPERATIONAL_GOLDEN["workflows"]) == REQUESTED_WORKFLOWS
    assert merge_route_sequence("empty_databases_merge_path") == tuple(
        _golden("empty_databases_merge_path")["completed_step_ids"]
    )
    assert merge_route_sequence("filled_databases_merge_path") == tuple(
        _golden("filled_databases_merge_path")["completed_step_ids"]
    )
