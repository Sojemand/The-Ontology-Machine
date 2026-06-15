from __future__ import annotations

from typing import Any

from .. import support_monitor


def build_summary_cards(*, module_root) -> list[dict]:
    del module_root
    support, support_error = _support_for_summary()
    active_count = int(support.get("incident_count") or 0)
    recent = support.get("incidents") if isinstance(support.get("incidents"), list) else []
    recent_lines = [
        f"{item.get('severity', 'error')}: {item.get('module_key', '')}.{item.get('action', '')} - {item.get('message', '')}"
        for item in recent[:3]
        if isinstance(item, dict)
    ]
    return [
        {
            "card_id": "mcp_role",
            "label": "Module Role",
            "body": "What this module is responsible for.",
            "lines": [
                "Transport: local stdio only; there is no network listener here.",
                "Responsibility: expose MCP tools and delegate to owner-local contracts.",
                "Boundary: the MCP Server does not implement a second business-logic world.",
                "Write rule: cross-module writes are allowed only through manifest-listed owner contracts.",
            ],
        },
        {
            "card_id": "support_monitor",
            "label": "Support Monitor",
            "body": "How installed systems turn runtime failures into actionable development reports.",
            "lines": [
                f"Support status: {'unavailable - ' + support_error if support_error else 'available'}",
                f"Active candidate incidents: {active_count}",
                f"Dismissed incidents: {support.get('dismissed_count', 0)}",
                f"Local support state: {support.get('support_state_root', '')}",
                "Support report work is split across assess/list/preview/build/queue/dismiss tools. Assessment returns an assessment_id.",
                "Only unexpected_exception, contract_regression, repeatable_product_failure, and data_corruption_risk may progress to report preview/build/queue.",
                "Missing paths, invalid user input, missing configuration, expected preflight failures, permission denials, external dependency failures, and unknown issues stay user-actionable instead of reportable.",
                "Report preview/build/queue actions require a reportable assessment_id; queue also requires user_confirmed=true.",
                "Queued reports still go to a local outbox only. A later connector can pick up that outbox and create a Git issue or repository ticket.",
                "Dismiss hides an issue from the active list when the user decides it is known, irrelevant, or already handled.",
                *(recent_lines or ["Recent incidents: none"]),
            ],
        },
    ]


def _support_for_summary() -> tuple[dict[str, Any], str]:
    try:
        return support_monitor.list_incidents(limit=5), ""
    except Exception as exc:
        return {"incident_count": 0, "dismissed_count": 0, "incidents": [], "support_state_root": ""}, str(exc)
