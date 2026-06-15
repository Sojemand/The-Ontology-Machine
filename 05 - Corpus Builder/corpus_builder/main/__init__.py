"""Path-stable CLI surface for Corpus Builder Vision."""
from __future__ import annotations

from types import SimpleNamespace

from ..context import ModuleContext
from ..search.policy_store import load_search_policy
from ..services import (
    apply_semantic_release,
    audit_semantics,
    backfill_semantics,
    build_load_bundle,
    export_corpus,
    get_stats,
    list_archived,
    load_batch,
    load_module_config,
    load_semantic_release,
    merge_corpus_databases,
    merge_preflight,
    resolve_corpus_db_path,
    search_corpus,
    semantic_status,
)
from ..standalone_artifacts import build_rebuild_bundles_from_artifacts, rebuild_corpus_from_artifacts
from . import adapter, corpus_workflow, ingest_workflow, semantic_workflow
from .surface import build_parser, dispatch_command

CONTEXT = ModuleContext.from_package_root()


def _service_seams() -> SimpleNamespace:
    return SimpleNamespace(
        apply_semantic_release=apply_semantic_release,
        audit_semantics=audit_semantics,
        backfill_semantics=backfill_semantics,
        build_load_bundle=build_load_bundle,
        build_rebuild_bundles_from_artifacts=build_rebuild_bundles_from_artifacts,
        export_corpus=export_corpus,
        get_stats=get_stats,
        list_archived=list_archived,
        load_batch=load_batch,
        load_module_config=load_module_config,
        load_search_policy=load_search_policy,
        load_semantic_release=load_semantic_release,
        merge_corpus_databases=merge_corpus_databases,
        merge_preflight=merge_preflight,
        rebuild_corpus_from_artifacts=rebuild_corpus_from_artifacts,
        resolve_corpus_db_path=resolve_corpus_db_path,
        search_corpus=search_corpus,
        semantic_status=semantic_status,
    )


def _setup_logging() -> None:
    adapter.setup_logging(CONTEXT)


def _run_load(args) -> None:
    ingest_workflow.run_load(args, context=CONTEXT, seams=_service_seams())


def _run_rebuild(args) -> None:
    ingest_workflow.run_rebuild(args, context=CONTEXT, seams=_service_seams())


def _run_search(args) -> None:
    corpus_workflow.run_search(args, context=CONTEXT, seams=_service_seams())


def _run_export(args) -> None:
    corpus_workflow.run_export(args, context=CONTEXT, seams=_service_seams())


def _run_stats(args) -> None:
    corpus_workflow.run_stats(args, context=CONTEXT, seams=_service_seams())


def _run_archived(args) -> None:
    corpus_workflow.run_archived(args, context=CONTEXT, seams=_service_seams())


def _run_semantic_status(args) -> None:
    semantic_workflow.run_semantic_status(args, context=CONTEXT, seams=_service_seams())


def _run_semantic_audit(args) -> None:
    semantic_workflow.run_semantic_audit(args, context=CONTEXT, seams=_service_seams())


def _run_semantic_load(args) -> None:
    semantic_workflow.run_semantic_load(args, context=CONTEXT, seams=_service_seams())


def _run_semantic_apply(args) -> None:
    semantic_workflow.run_semantic_apply(args, context=CONTEXT, seams=_service_seams())


def _run_semantic_backfill(args) -> None:
    semantic_workflow.run_semantic_backfill(args, context=CONTEXT, seams=_service_seams())


def _run_merge_preflight(args) -> None:
    semantic_workflow.run_merge_preflight(args, context=CONTEXT, seams=_service_seams())


def _run_merge_corpus(args) -> None:
    semantic_workflow.run_merge_corpus(args, context=CONTEXT, seams=_service_seams())


def main(argv: list[str] | None = None) -> None:
    _setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch_command(
        args,
        show_help=parser.print_help,
        run_load=_run_load,
        run_rebuild=_run_rebuild,
        run_search=_run_search,
        run_export=_run_export,
        run_stats=_run_stats,
        run_archived=_run_archived,
        run_semantic_status=_run_semantic_status,
        run_semantic_audit=_run_semantic_audit,
        run_semantic_load=_run_semantic_load,
        run_semantic_apply=_run_semantic_apply,
        run_semantic_backfill=_run_semantic_backfill,
        run_merge_preflight=_run_merge_preflight,
        run_merge_corpus=_run_merge_corpus,
    )


__all__ = [
    "CONTEXT",
    "_run_archived",
    "_run_export",
    "_run_load",
    "_run_merge_corpus",
    "_run_merge_preflight",
    "_run_rebuild",
    "_run_search",
    "_run_semantic_apply",
    "_run_semantic_audit",
    "_run_semantic_backfill",
    "_run_semantic_load",
    "_run_semantic_status",
    "_run_stats",
    "_setup_logging",
    "apply_semantic_release",
    "audit_semantics",
    "backfill_semantics",
    "build_load_bundle",
    "build_parser",
    "build_rebuild_bundles_from_artifacts",
    "dispatch_command",
    "export_corpus",
    "get_stats",
    "list_archived",
    "load_batch",
    "load_module_config",
    "load_search_policy",
    "load_semantic_release",
    "merge_corpus_databases",
    "merge_preflight",
    "main",
    "rebuild_corpus_from_artifacts",
    "resolve_corpus_db_path",
    "search_corpus",
    "semantic_status",
]
