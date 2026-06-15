from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.merge import MergeWorkflowBlocker
from semantic_control_kernel.workflows.merge.receipts import blocker_from_adapter_result


def backfill_sql(corpus_adapter: object, payload: Mapping[str, Any]) -> tuple[object | None, MergeWorkflowBlocker | None]:
    if not payload.get("backfill_required"):
        return None, None
    result = corpus_adapter.backfill_sql(payload)
    return result, blocker_from_adapter_result("backfill_sql", result, function_name="backfill_sql")
