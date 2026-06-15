from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

MODULE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_OPERATIONAL_GOLDEN_PATH = MODULE_ROOT / "dev-tests" / "fixtures" / "phase12" / "frozen_operational_workflows.json"
REQUESTED_WORKFLOWS = (
    "database_merge_additive_only",
    "empty_databases_merge_path",
    "filled_databases_merge_path",
    "database_rebuild_from_artifacts",
    "reset_database",
    "manual_pipeline_run",
)
PIPELINE_BATCH_PLACEHOLDER = "<pipeline_batch_id>"
RESET_MANIFEST_PLACEHOLDER = "<reset_manifest_id>.json"
PIPELINE_BATCH_RE = re.compile(r"pbt_\d{14}_[0-9a-f]{8}_\d+")
RESET_MANIFEST_RE = re.compile(r"rstman_[0-9a-f]{18}\.json")

def _load_golden() -> dict[str, Any]:
    if not FROZEN_OPERATIONAL_GOLDEN_PATH.exists():
        return {"schema_version": "", "workflows": []}
    return json.loads(FROZEN_OPERATIONAL_GOLDEN_PATH.read_text(encoding="utf-8"))

FROZEN_OPERATIONAL_GOLDEN = _load_golden()
FROZEN_OPERATIONAL_CASES = tuple(FROZEN_OPERATIONAL_GOLDEN.get("workflows", ()))


@dataclass
class FreezeRun:
    execution: Any
    artifact_root: Path
    adapters: Mapping[str, Any]


def _golden(workflow_tool: str) -> dict[str, Any]:
    return next(entry for entry in FROZEN_OPERATIONAL_GOLDEN["workflows"] if entry["workflow_tool"] == workflow_tool)
