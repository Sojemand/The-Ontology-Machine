from __future__ import annotations

import json
from pathlib import Path

from .manifest import SuiteManifest


ALLOWED_COVERAGE_STATUS = {
    "tested_click",
    "tested_action",
    "covered_by_contract",
    "covered_by_workflow",
    "manual_only_with_reason",
    "deferred_with_issue",
}


def expected_inventory(suite: SuiteManifest) -> list[dict]:
    raw_inventory = suite.raw.get("expected_inventory", [])
    return [dict(item) for item in raw_inventory]


def validate_inventory_gate(suite: SuiteManifest) -> list[str]:
    if not suite.inventory_gate:
        return []
    errors: list[str] = []
    for index, item in enumerate(expected_inventory(suite), start=1):
        action_key = str(item.get("action_key") or "")
        coverage = str(item.get("coverage") or "")
        if not action_key:
            errors.append(f"inventory item {index} has no action_key")
        if coverage not in ALLOWED_COVERAGE_STATUS:
            errors.append(f"inventory item {action_key or index} has invalid coverage: {coverage}")
        if coverage == "manual_only_with_reason" and not item.get("reason"):
            errors.append(f"inventory item {action_key or index} is manual-only without reason")
        if coverage == "deferred_with_issue" and not item.get("issue"):
            errors.append(f"inventory item {action_key or index} is deferred without issue")
    return errors


def write_inventory_report(path: Path, suites: list[SuiteManifest]) -> Path:
    payload = {
        "schema_version": 1,
        "suites": [
            {
                "name": suite.name,
                "display_name": suite.display_name,
                "inventory_gate": suite.inventory_gate,
                "expected_inventory": expected_inventory(suite),
            }
            for suite in suites
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
