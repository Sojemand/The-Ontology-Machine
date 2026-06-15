"""Surface stage for parser construction and command dispatch."""
from __future__ import annotations

import argparse
from collections.abc import Callable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corpus-builder-vision",
        description="Corpus Builder Vision - SQLite Persistenz + Suche + Export",
    )
    sub = parser.add_subparsers(dest="command")
    _add_load_parser(sub)
    _add_rebuild_parser(sub)
    _add_search_parser(sub)
    _add_export_parser(sub)
    _add_stats_parser(sub)
    _add_archived_parser(sub)
    _add_semantic_status_parser(sub)
    _add_semantic_audit_parser(sub)
    _add_load_release_parser(sub)
    _add_apply_release_parser(sub)
    _add_backfill_parser(sub)
    _add_merge_preflight_parser(sub)
    _add_merge_parser(sub)
    return parser


def dispatch_command(
    args: argparse.Namespace,
    *,
    show_help: Callable[[], None],
    run_load: Callable[[argparse.Namespace], None],
    run_rebuild: Callable[[argparse.Namespace], None],
    run_search: Callable[[argparse.Namespace], None],
    run_export: Callable[[argparse.Namespace], None],
    run_stats: Callable[[argparse.Namespace], None],
    run_archived: Callable[[argparse.Namespace], None],
    run_semantic_status: Callable[[argparse.Namespace], None],
    run_semantic_audit: Callable[[argparse.Namespace], None],
    run_semantic_load: Callable[[argparse.Namespace], None],
    run_semantic_apply: Callable[[argparse.Namespace], None],
    run_semantic_backfill: Callable[[argparse.Namespace], None],
    run_merge_preflight: Callable[[argparse.Namespace], None],
    run_merge_corpus: Callable[[argparse.Namespace], None],
) -> None:
    command = getattr(args, "command", None)
    if command is None:
        show_help()
        return

    dispatch = {
        "load": run_load,
        "rebuild": run_rebuild,
        "search": run_search,
        "export": run_export,
        "stats": run_stats,
        "archived": run_archived,
        "semantic-status": run_semantic_status,
        "semantic-audit": run_semantic_audit,
        "load-release": run_semantic_load,
        "apply-release": run_semantic_apply,
        "backfill-stale": run_semantic_backfill,
        "merge-preflight": run_merge_preflight,
        "merge-corpus": run_merge_corpus,
    }
    dispatch[command](args)


def _add_load_parser(subparsers) -> None:
    parser = subparsers.add_parser("load", help="Technischen Einzel-Load ausfuehren")
    parser.add_argument("--input", required=True, help="Pfad zu *.structured.normalized.json")
    parser.add_argument("--validation-report", default=None, help="Pfad zum Validator-Report fuer Structured-Evidence")
    parser.add_argument("--structured-evidence", default=None, help="Optionaler structured.json-Pfad fuer normalized-first Eingaben")
    parser.add_argument("--raw-evidence", default=None, help="Optionaler raw.json-Pfad als kalter Residual-Layer")
    parser.add_argument("--corpus-db", default=None, help="Pfad zu corpus.db")


def _add_rebuild_parser(subparsers) -> None:
    parser = subparsers.add_parser("rebuild", help="corpus.db aus Pipeline-Artefakten neu aufbauen")
    parser.add_argument("--pipeline-root", default=None, help="Pipeline-Artefaktordner mit normalized/structured/validation/raw_extracts")
    parser.add_argument("--normalized-dir", default=None, help="Optionaler Override fuer den normalized-Ordner")
    parser.add_argument("--structured-dir", default=None, help="Optionaler Override fuer den structured-Ordner")
    parser.add_argument("--validation-dir", default=None, help="Optionaler Override fuer den validation-Ordner")
    parser.add_argument("--raw-dir", default=None, help="Optionaler Override fuer den raw_extracts-Ordner")
    parser.add_argument("--corpus-db", default=None, help="Pfad zu corpus.db")
    parser.add_argument("--keep-existing", action="store_true", help="Bestehende DB nicht vorher loeschen")


def _add_search_parser(subparsers) -> None:
    parser = subparsers.add_parser("search", help="Corpus durchsuchen")
    parser.add_argument("--query", required=True, help="Suchtext")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--corpus-db", default=None)


def _add_export_parser(subparsers) -> None:
    parser = subparsers.add_parser("export", help="Corpus exportieren")
    parser.add_argument("--format", choices=["jsonl", "csv"], required=True)
    parser.add_argument("--output", required=True, help="Ausgabedatei")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--corpus-db", default=None)


def _add_stats_parser(subparsers) -> None:
    parser = subparsers.add_parser("stats", help="Corpus-Statistiken")
    parser.add_argument("--corpus-db", default=None)


def _add_archived_parser(subparsers) -> None:
    parser = subparsers.add_parser("archived", help="Archivierte Dokumente anzeigen")
    parser.add_argument("--corpus-db", default=None)


def _add_semantic_status_parser(subparsers) -> None:
    parser = subparsers.add_parser("semantic-status", help="Aktiven Semantic-Release-Status anzeigen")
    parser.add_argument("--corpus-db", default=None)


def _add_semantic_audit_parser(subparsers) -> None:
    parser = subparsers.add_parser("semantic-audit", help="Veroeffentlichten Semantic Release auditieren")
    parser.add_argument("--corpus-db", default=None)


def _add_load_release_parser(subparsers) -> None:
    parser = subparsers.add_parser("load-release", help="Neuen Semantic Release laden, aber noch nicht aktivieren")
    parser.add_argument("--release", required=True, help="Pfad zum veroeffentlichten Semantic Release JSON")
    parser.add_argument("--corpus-db", default=None)


def _add_apply_release_parser(subparsers) -> None:
    parser = subparsers.add_parser("apply-release", help="Veroeffentlichten Semantic Release aktivieren")
    parser.add_argument("--corpus-db", default=None)


def _add_backfill_parser(subparsers) -> None:
    parser = subparsers.add_parser("backfill-stale", help="Selektive semantische Rematerialisierung")
    parser.add_argument("--corpus-db", default=None)
    parser.add_argument("--document-id", action="append", dest="document_ids", default=None)
    parser.add_argument("--all", action="store_true", help="Alle aktiven Dokumente statt nur stale rematerialisieren")
    parser.add_argument("--limit", type=int, default=None)


def _add_merge_preflight_parser(subparsers) -> None:
    parser = subparsers.add_parser("merge-preflight", help="Inspect-only Preflight fuer snapshot-first DB-Merge")
    parser.add_argument("--source-db", required=True, help="Pfad zur Quell-corpus.db")
    parser.add_argument("--target-db", required=True, help="Pfad zur Ziel-corpus.db")


def _add_merge_parser(subparsers) -> None:
    parser = subparsers.add_parser("merge-corpus", help="Snapshot-first DB-Merge mit expliziten Bestatigungsartefakten")
    parser.add_argument("--source-db", required=True, help="Pfad zur Quell-corpus.db")
    parser.add_argument("--target-db", required=True, help="Pfad zur Ziel-corpus.db")
    parser.add_argument("--snapshot-risk-confirmation", default=None, help="Pfad zum Snapshot-Risk-Confirmation-Artefakt")
    parser.add_argument("--collision-resolution", default=None, help="Pfad zum globalen Collision-Resolution-Artefakt")


__all__ = ["build_parser", "dispatch_command"]
