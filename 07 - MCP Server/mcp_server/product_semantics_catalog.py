from __future__ import annotations

from typing import Any

from .semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES


NON_KERNEL_MCP_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "inspect_current_environment_status", "inspect_pipeline_contract_governance",
        "inspect_pipeline_product_context", "explain_pipeline_capabilities",
        "recommend_pipeline_next_steps", "review_source_document_taxonomy_coverage",
        "review_source_sample_set_taxonomy_coverage", "read_active_semantic_release",
        "semantic_audit", "search_corpus", "corpus_stats", "export_corpus",
        "assess_support_incident", "list_support_incidents", "preview_support_bug_report",
        "build_support_bug_report", "queue_support_bug_report", "dismiss_support_incident",
    }
)

KERNEL_TOOL_SUMMARY_TEXT: dict[str, str] = {
    "kernel_status": "Liest den aktuellen Semantic-Control-Kernel-Zustand fuer die aktive Datenbank und den Artefaktbaum.",
    "empty_database_no_semantic_release": "Startet eine leere Datenbank ohne Semantic Release als bewusst blockierten Startpunkt.",
    "empty_database_default_taxonomy_default_projections": "Erzeugt eine sofort lauffaehige leere Datenbank mit Standard-Taxonomie und Standard-Projections.",
    "empty_database_default_taxonomy_no_projections": "Erzeugt eine leere Datenbank mit persistierter Standard-Taxonomie ohne Projections; Custom-Projections muessen danach ueber Kernel-Resume ergaenzt werden.",
    "create_custom_taxonomy_path": "Startet den Pfad fuer eine benutzerdefinierte Taxonomie aus Beispieldokumenten.",
    "create_custom_projection_path": "Startet den Pfad fuer benutzerdefinierte Projections auf Basis einer vorhandenen Taxonomie.",
    "manual_pipeline_run": "Startet einen benutzerseitigen Pipeline-Lauf fuer die aktive Datenbank.",
    "database_merge_additive_only": "Fuehrt mehrere Datenbanken ueber den additiven Merge-Pfad des Kernels zusammen.",
    "database_rebuild_from_artifacts": "Baut eine Datenbank aus vorhandenen Artefakten unter Kernel-Kontrolle neu auf.",
    "reset_database": "Leert die aktive Datenbank nach Bestaetigung und erhaelt den Kernel-Regelstand.",
}


def kernel_tool_summaries(*, limit: int, preferred: list[str] | None = None) -> list[dict[str, Any]]:
    return [
        {"tool_name": name, "summary_de": KERNEL_TOOL_SUMMARY_TEXT.get(name, auto_summary(name)), "surface": "semantic_control_kernel"}
        for name in ordered_tool_names(preferred or [], list(PERMANENT_AGENT_TOOL_NAMES))[:limit]
    ]


def auto_summary(tool_name: str) -> str:
    return str(tool_name).replace("_", " ")


def ordered_tool_names(preferred: list[str], fallback: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for tool_name in [*preferred, *fallback]:
        name = str(tool_name or "").strip()
        if name and name not in seen:
            ordered.append(name)
            seen.add(name)
    return ordered
