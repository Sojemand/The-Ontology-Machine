from __future__ import annotations

from typing import Any

from .product_semantics_cards import CARDS
from .product_semantics_playbooks import PLAYBOOKS
from .product_semantics_support import (
    alternatives,
    capabilities_message,
    capability_groups,
    context_next_kernel_tools,
    context_next_mcp_tools,
    context_summary_de,
    kernel_tool_summaries,
    known_context_note,
    normalize_text,
    path_from_playbook,
    phrase_matches,
    recommendation_message,
    safe_call,
)

PRODUCT_SEMANTICS_VERSION = "pipeline_product_semantics_v1"


def inspect_product_context(arguments: dict[str, Any]) -> dict[str, Any]:
    include_catalog = _bool(
        arguments.get("include_kernel_tool_summary")
        if arguments.get("include_kernel_tool_summary") is not None
        else arguments.get("include_workflow_catalog"),
        default=True,
    )
    max_workflows = _positive_int(arguments.get("max_kernel_tools") or arguments.get("max_workflows"), default=12, maximum=40)
    from .tool_handlers_workspace_status import inspect_current_environment_status

    environment = safe_call(lambda: inspect_current_environment_status({}))
    safe_next_kernel_tools = context_next_kernel_tools(environment)
    safe_next_mcp_tools = context_next_mcp_tools(environment)
    workflows = kernel_tool_summaries(limit=max_workflows, preferred=safe_next_kernel_tools) if include_catalog else []
    return {
        "status": "ok",
        "question_contract": "pipeline_product_advisory",
        "product_semantics_version": PRODUCT_SEMANTICS_VERSION,
        "current_environment": environment,
        "kernel_tool_summary": {
            "included": include_catalog,
            "tool_count": len(workflows),
            "items": workflows,
        },
        "context_summary_de": context_summary_de(environment),
        "safe_next_kernel_tools": safe_next_kernel_tools,
        "safe_next_mcp_tools": safe_next_mcp_tools,
        "user_message_de": "Ich habe Pipeline-Kontext und Kernel-/MCP-Einstiege als Produktkontext gelesen.",
    }


def explain_capabilities(arguments: dict[str, Any]) -> dict[str, Any]:
    question = _text(arguments.get("question") or arguments.get("goal") or "")
    focus = _text(arguments.get("focus") or "")
    cards = _select_cards(question, focus=focus)
    playbooks = _select_playbooks(question, focus=focus)
    return {
        "status": "ok",
        "question_contract": "pipeline_product_advisory",
        "product_semantics_version": PRODUCT_SEMANTICS_VERSION,
        "advisory_mode": "capabilities",
        "question": question,
        "concept_cards": cards,
        "goal_playbooks": playbooks,
        "capability_groups": capability_groups(),
        "safe_next_kernel_tools": _unique([tool for pb in playbooks for tool in pb.get("safe_next_kernel_tools", [])]),
        "safe_next_mcp_tools": _unique([tool for pb in playbooks for tool in pb.get("safe_next_mcp_tools", [])]),
        "user_message_de": capabilities_message(cards, playbooks),
    }


def recommend_next_steps(arguments: dict[str, Any]) -> dict[str, Any]:
    goal = _text(arguments.get("goal") or arguments.get("question") or "")
    focus = _text(arguments.get("focus") or "")
    known_context = arguments.get("known_context") if isinstance(arguments.get("known_context"), dict) else {}
    playbooks = _select_playbooks(goal, focus=focus)
    primary = playbooks[0] if playbooks else _default_playbook()
    context_note = known_context_note(known_context)
    return {
        "status": "ok",
        "question_contract": "pipeline_product_advisory",
        "product_semantics_version": PRODUCT_SEMANTICS_VERSION,
        "advisory_mode": "next_steps",
        "goal": goal,
        "context_note_de": context_note,
        "recommended_path": path_from_playbook(primary),
        "alternatives": alternatives(primary),
        "concept_cards": _select_cards(goal, focus=focus, minimum=("database", "semantic_release")),
        "safe_next_kernel_tools": _unique(list(primary.get("safe_next_kernel_tools", []))),
        "safe_next_mcp_tools": _unique(list(primary.get("safe_next_mcp_tools", []))),
        "user_message_de": recommendation_message(primary, context_note),
    }


def _select_cards(text: str, *, focus: str = "", minimum: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    normalized = normalize_text(f"{text} {focus}")
    scored = []
    for card in CARDS:
        score = sum(1 for item in card["keywords"] if phrase_matches(normalized, str(item)))
        if card["concept_id"] in minimum:
            score += 5
        scored.append((score, card))
    chosen = [card for score, card in sorted(scored, key=lambda item: (item[0], item[1]["title"]), reverse=True) if score > 0]
    if not chosen:
        chosen = [card for card in CARDS if card["concept_id"] in {"database", "semantic_release", "input_folder", "search_quality"}]
    return [_public_item(card) for card in chosen[:6]]


def _select_playbooks(text: str, *, focus: str = "") -> list[dict[str, Any]]:
    normalized = normalize_text(f"{text} {focus}")
    scored = []
    for playbook in PLAYBOOKS:
        score = sum(1 for item in playbook["keywords"] if phrase_matches(normalized, str(item)))
        scored.append((score, playbook))
    chosen = [
        pb
        for score, pb in sorted(
            scored,
            key=lambda item: (item[0], item[1]["playbook_id"] != "what_can_i_do", item[1]["title"]),
            reverse=True,
        )
        if score > 0
    ]
    if not chosen:
        chosen = [_default_playbook()]
    return [_public_item(playbook) for playbook in chosen[:4]]


def _default_playbook() -> dict[str, Any]:
    return _public_item(next(item for item in PLAYBOOKS if item["playbook_id"] == "what_can_i_do"))


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "keywords"}


def _bool(value: Any, *, default: bool) -> bool:
    return default if value in (None, "") else bool(value)


def _positive_int(value: Any, *, default: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(maximum, number))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _unique(items: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(item) for item in items if str(item).strip())]


__all__ = [
    "PRODUCT_SEMANTICS_VERSION",
    "explain_capabilities",
    "inspect_product_context",
    "recommend_next_steps",
]
