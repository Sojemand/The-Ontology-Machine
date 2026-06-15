from __future__ import annotations

import re
import unicodedata
from typing import Any
from .product_semantics_catalog import KERNEL_TOOL_SUMMARY_TEXT, NON_KERNEL_MCP_TOOL_NAMES, auto_summary, kernel_tool_summaries


def capability_groups() -> list[dict[str, Any]]:
    return [
        {
            "group_id": "understand",
            "label_de": "Verstehen",
            "kernel_tool_names": ["kernel_status"],
            "mcp_tool_names": ["inspect_current_environment_status", "inspect_pipeline_product_context"],
        },
        {
            "group_id": "process",
            "label_de": "Verarbeiten",
            "kernel_tool_names": ["manual_pipeline_run", "empty_database_default_taxonomy_default_projections", "empty_database_default_taxonomy_no_projections"],
            "mcp_tool_names": [],
        },
        {
            "group_id": "improve_rules",
            "label_de": "Regeln verbessern",
            "kernel_tool_names": ["create_custom_taxonomy_path", "create_custom_projection_path"],
            "mcp_tool_names": ["review_source_document_taxonomy_coverage", "review_source_sample_set_taxonomy_coverage"],
        },
        {
            "group_id": "rebuild",
            "label_de": "Neuaufbau und Reparatur",
            "kernel_tool_names": ["database_rebuild_from_artifacts", "reset_database", "kernel_status"],
            "mcp_tool_names": ["assess_support_incident"],
        },
        {
            "group_id": "export",
            "label_de": "Export und Suche",
            "kernel_tool_names": ["kernel_status"],
            "mcp_tool_names": ["search_corpus", "corpus_stats", "export_corpus"],
        },
    ]


def path_from_playbook(playbook: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_kernel_tool": _text_or_none(playbook.get("recommended_first_kernel_tool")),
        "first_mcp_tool": _text_or_none(playbook.get("recommended_first_mcp_tool")),
        "first_step_de": playbook["recommended_first_step_de"],
        "why_de": playbook["why_de"],
        "related_kernel_tool_names": list(playbook.get("safe_next_kernel_tools", [])),
        "related_mcp_tool_names": list(playbook.get("safe_next_mcp_tools", [])),
    }


def alternatives(playbook: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    first_kernel = _text_or_none(playbook.get("recommended_first_kernel_tool"))
    first_mcp = _text_or_none(playbook.get("recommended_first_mcp_tool"))
    for tool_name in playbook.get("safe_next_kernel_tools", []):
        if tool_name != first_kernel:
            result.append({"tool_name": str(tool_name), "tool_surface": "semantic_control_kernel", "why_de": KERNEL_TOOL_SUMMARY_TEXT.get(str(tool_name), auto_summary(str(tool_name)))})
    for tool_name in playbook.get("safe_next_mcp_tools", []):
        if tool_name != first_mcp:
            result.append({"tool_name": str(tool_name), "tool_surface": "mcp", "why_de": auto_summary(str(tool_name))})
    return result


def context_summary_de(environment: dict[str, Any]) -> str:
    if not environment or environment.get("status") == "error":
        return "Der aktive Pipeline-Kontext konnte nicht vollstaendig gelesen werden."
    db = "vorhanden" if environment.get("database_present") else "nicht sichtbar"
    workspace = "vorhanden" if environment.get("workspace_present") else "nicht sichtbar"
    input_count = int(environment.get("input_file_count") or 0)
    return f"Aktuelle Datenbank: {db}. Workspace: {workspace}. Input-Dateien: {input_count}."


def context_next_kernel_tools(environment: dict[str, Any]) -> list[str]:
    if not environment or environment.get("status") == "error":
        return ["kernel_status"]
    if not environment.get("workspace_present") or not environment.get("database_present"):
        return ["kernel_status", "empty_database_default_taxonomy_default_projections", "empty_database_default_taxonomy_no_projections", "empty_database_no_semantic_release"]
    if int(environment.get("input_file_count") or 0) > 0:
        return ["manual_pipeline_run", "create_custom_taxonomy_path", "create_custom_projection_path"]
    return ["kernel_status", "create_custom_taxonomy_path", "create_custom_projection_path"]


def context_next_mcp_tools(environment: dict[str, Any]) -> list[str]:
    if not environment or environment.get("status") == "error":
        return ["inspect_current_environment_status"]
    if not environment.get("workspace_present") or not environment.get("database_present"):
        return ["inspect_current_environment_status"]
    if int(environment.get("input_file_count") or 0) > 0:
        return ["inspect_current_environment_status"]
    return ["search_corpus", "corpus_stats", "export_corpus"]


def capabilities_message(cards: list[dict[str, Any]], playbooks: list[dict[str, Any]]) -> str:
    first = cards[0]["title"] if cards else "Datenbank"
    playbook = playbooks[0]["title"] if playbooks else "Was kann ich mit der Datenbank tun?"
    return f"Ich kann das als Produktfrage beantworten: zentral sind hier {first} und der naechste Entscheidungsrahmen '{playbook}'."


def recommendation_message(playbook: dict[str, Any], context_note: str) -> str:
    return f"Meine Empfehlung: {playbook['recommended_first_step_de']} {context_note}".strip()


def known_context_note(known_context: dict[str, Any]) -> str:
    if not known_context:
        return "Wenn kein aktueller Zustand bekannt ist, sollte der Agent zuerst read-only den Pipeline-Kontext pruefen."
    status = known_context.get("status") or known_context.get("latest_run_status") or ""
    return f"Bekannter Kontext wurde beruecksichtigt: {status or 'vorhanden'}."


def safe_call(fn) -> dict[str, Any]:
    try:
        result = fn()
        return result if isinstance(result, dict) else {"status": "unknown"}
    except Exception as exc:  # noqa: BLE001 - advisory must stay explanatory
        return {"status": "error", "error_type": type(exc).__name__}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def phrase_matches(normalized_text: str, phrase: str) -> bool:
    needle = normalize_text(phrase)
    if not needle:
        return False
    return needle in normalized_text


def _text_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


__all__ = [
    "alternatives",
    "capabilities_message",
    "capability_groups",
    "context_next_kernel_tools",
    "context_next_mcp_tools",
    "context_summary_de",
    "kernel_tool_summaries",
    "known_context_note",
    "normalize_text",
    "path_from_playbook",
    "phrase_matches",
    "recommendation_message",
    "safe_call",
    "NON_KERNEL_MCP_TOOL_NAMES",
]
