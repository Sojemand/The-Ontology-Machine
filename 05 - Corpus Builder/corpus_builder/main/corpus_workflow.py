"""Workflow stages for corpus DB CLI commands."""
from __future__ import annotations

from types import SimpleNamespace

from ..stats import print_stats


def run_search(args, *, context, seams: SimpleNamespace) -> None:
    policy = seams.load_search_policy(context.module_root)
    default_limit = int(policy["fulltext"]["limit_default"])
    limit = _positive_or_default(getattr(args, "limit", None), default_limit)
    results = seams.search_corpus(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
        query=args.query,
        mode="Volltext (FTS)",
        limit=limit,
    )
    if not results:
        print("Keine Ergebnisse.")
        return

    for index, result in enumerate(results, 1):
        print(f"\n[{index}] {result.title or '(kein Titel)'}")
        print(f"    ID:    {result.document_id}")
        print(f"    Score: {result.score:.4f} ({result.source})")
        if result.description:
            print(f"    {result.description[:100]}")
        if result.snippet:
            print(f"    ...{result.snippet}...")


def run_export(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.export_corpus(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
        output_path=args.output,
        fmt=args.format,
        include_archived=bool(args.include_archived),
    )
    print(f"Export: {result.document_count} Dokumente nach {result.path} ({result.format})")


def run_stats(args, *, context, seams: SimpleNamespace) -> None:
    stats = seams.get_stats(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )
    print_stats(stats)


def run_archived(args, *, context, seams: SimpleNamespace) -> None:
    rows = seams.list_archived(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )
    if not rows:
        print("Keine archivierten Dokumente.")
        return

    print(f"\n{'ID':36s}  {'Datei':30s}  {'Archiviert':20s}  Nachfolger")
    print("-" * 120)
    for row in rows:
        print(
            f"{row['id']:36s}  {row['file_name']:30s}  "
            f"{row['archived_at'] or '':20s}  {row['superseded_by'] or '-'}"
        )


def _positive_or_default(value: int | None, default: int) -> int:
    try:
        normalized = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(1, normalized)


__all__ = ["run_archived", "run_export", "run_search", "run_stats"]
