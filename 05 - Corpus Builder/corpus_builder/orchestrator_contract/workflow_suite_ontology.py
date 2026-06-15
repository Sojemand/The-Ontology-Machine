"""Ontology contract handlers for Corpus Builder-owned deterministic workflows."""

from __future__ import annotations

from ..services import run_basic_relation_mining
from .result_envelope import build_result, kv_artifacts


def handle_basic_relation_mining(command, *, context, run_basic_relation_mining_fn=run_basic_relation_mining):
    detail = run_basic_relation_mining_fn(
        context,
        corpus_db_path=command.corpus_db_path,
        dry_run=command.dry_run,
    )
    report = dict(detail.get("report") or {})
    response = build_result(
        headline="Basic relation mining completed",
        summary_lines=[
            f"Status: {report.get('status') or detail.get('status') or 'unknown'}",
            f"Source documents: {report.get('source_documents', 0)}",
            f"Source document pages: {report.get('source_document_pages', 0)}",
            f"Relations inserted: {report.get('relations_inserted', 0)}",
        ],
        artifacts=kv_artifacts([("Corpus DB", detail.get("corpus_db_path"))]),
        detail=detail,
    )
    response["output_refs"] = {
        "database_path": detail.get("corpus_db_path") or "",
        "corpus_db_path": detail.get("corpus_db_path") or "",
        "source_documents": int(report.get("source_documents") or 0),
        "source_document_pages": int(report.get("source_document_pages") or 0),
        "relations_inserted": int(report.get("relations_inserted") or 0),
        "unresolved_documents": list(report.get("unresolved_documents") or []),
        "rejected_groups": list(report.get("rejected_groups") or []),
        "warnings": list(report.get("warnings") or []),
    }
    response["receipt_fields"] = {
        "owner_module": "05 - Corpus Builder",
        "owner_action": "basic_relation_mining",
    }
    return response


__all__ = ["handle_basic_relation_mining", "run_basic_relation_mining"]
