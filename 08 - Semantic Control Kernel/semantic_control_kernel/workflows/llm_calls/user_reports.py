from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


DIRECT_CHAT_REPORT_GUIDANCE: dict[str, Any] = {
    "response_mode": "emit_direct_message",
    "message_role": "assistant",
    "message_source": "user_visible_summary",
    "suppress_kernel_history": True,
}


def report_request_for_analysis(function_name: str, analysis_output: Any) -> tuple[str, Mapping[str, Any]] | None:
    if not isinstance(analysis_output, Mapping):
        return None
    if function_name == "analyze_samples":
        seed = analysis_output.get("user_report_samples_seed")
        if isinstance(seed, Mapping) and seed:
            return "user_report_samples", deepcopy(dict(seed))
        return None
    return None


def analysis_report_state_summary(function_name: str) -> str:
    if function_name == "user_report_samples":
        return "Sample analysis report ready for the active Pipeline session."
    return "Analysis report ready for the active Pipeline session."


def analysis_report_unavailable_summary(function_name: str) -> str:
    if function_name == "user_report_samples":
        return "Sample analysis report unavailable; workflow continued without the optional report."
    return "Analysis report unavailable; workflow continued without the optional report."


def analysis_report_mirror_payload(*, report_function: str, report_text: str, analysis_run_id: str) -> dict[str, Any]:
    return {
        "event_type": "progress",
        "severity": "info",
        "summary": report_text,
        "current_state_summary": analysis_report_state_summary(report_function),
        "extra": {
            "agent_explanation_guidance": deepcopy(DIRECT_CHAT_REPORT_GUIDANCE),
            "technical_detail_ref": {
                "kind": "analysis_report",
                "llm_function_name": report_function,
                "analysis_run_id": analysis_run_id,
            },
        },
    }


def analysis_report_unavailable_mirror_payload(
    *,
    report_function: str,
    analysis_run_id: str,
    unavailable_detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_type": "progress",
        "severity": "warning",
        "summary": analysis_report_unavailable_summary(report_function),
        "current_state_summary": "Optional analysis report unavailable; workflow continued.",
        "extra": {
            "technical_detail_ref": {
                "kind": "analysis_report_unavailable",
                "llm_function_name": report_function,
                "analysis_run_id": analysis_run_id,
                "unavailable_detail": dict(unavailable_detail or {}),
            },
        },
    }
