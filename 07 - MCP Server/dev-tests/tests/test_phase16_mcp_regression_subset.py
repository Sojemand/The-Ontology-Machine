from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SUBSET_MODULES = {
    "dev-tests/tests/test_agent_permissions.py",
    "dev-tests/tests/test_contract_healthcheck.py",
    "dev-tests/tests/test_protocol.py",
    "dev-tests/tests/test_tool_contract_matrix_golden.py",
    "dev-tests/tests/test_tool_handlers_product_advisory.py",
    "dev-tests/tests/test_tool_subprocess_core.py",
}


def test_phase15_disposition_selects_the_phase16_non_kernel_regression_subset() -> None:
    disposition = json.loads((MODULE_ROOT / "migration" / "phase15_legacy_test_disposition.json").read_text(encoding="utf-8"))
    kept = {
        str(entry["path"])
        for entry in disposition["entries"]
        if str(entry["disposition"]) == "keep_non_kernel_test_after_rewrite"
    }

    assert kept == EXPECTED_SUBSET_MODULES
