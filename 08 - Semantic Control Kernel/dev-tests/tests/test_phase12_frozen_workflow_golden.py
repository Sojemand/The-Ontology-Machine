from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from phase12_frozen_inventory import FROZEN_OPERATIONAL_CASES
from phase12_frozen_observation import _freeze_observation, _live_path_assertions
from phase12_frozen_runners import _RUNNERS


@pytest.mark.parametrize(
    "golden",
    FROZEN_OPERATIONAL_CASES,
    ids=[entry["workflow_tool"] for entry in FROZEN_OPERATIONAL_CASES],
)
def test_frozen_operational_workflows_match_golden_paths_artifacts_and_live_state(tmp_path: Path, golden: dict[str, Any]) -> None:
    workflow_tool = str(golden["workflow_tool"])
    run = _RUNNERS[workflow_tool](tmp_path)

    assert _freeze_observation(run, workflow_tool) == golden
    assert _live_path_assertions(run, workflow_tool) == golden["live_path_assertions"]
