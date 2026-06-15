"""Adapter stage for human-readable corpus stats rendering."""

from __future__ import annotations

from .types import CorpusStats

GROUP_SECTIONS = [
    ("Dokumenttypen", "by_document_type"),
    ("Kategorien", "by_category"),
    ("Sprachen", "by_language"),
    ("Validator-Status", "by_validator_status"),
    ("Promotion Slots", "by_promotion_slot"),
    ("Projectionen", "by_projection"),
    ("Materialisierung", "by_materialization_state"),
    ("Entity-Typen", "by_entity_type"),
]

TOP_SECTIONS = [
    ("Top Tags", "top_tags"),
    ("Top Personen", "top_people"),
    ("Top Organisationen", "top_organizations"),
    ("Top Field-Keys", "top_field_keys"),
    ("Top Promotions", "top_promotion_values"),
]


def format_stats(stats: CorpusStats) -> str:
    """Format stats as a human-readable text report."""
    lines = [
        f"{'=' * 60}",
        "  CORPUS STATISTIKEN",
        f"{'=' * 60}",
        "",
        f"  Dokumente:     {stats['total_documents']}",
        f"  Archiviert:    {stats['total_archived']}",
        f"  Fields:        {stats['total_fields']}",
        f"  Relations:     {stats['total_relations']}",
        f"  Entitaeten:    {stats['total_entities']}",
        f"  Stale Docs:    {stats['stale_documents']}",
        f"  Embeddings:    {stats['embeddings_count']}",
    ]

    _append_optional_summary(lines, stats)
    _append_group_sections(lines, stats)
    _append_top_sections(lines, stats)
    lines.extend(["", f"{'=' * 60}"])
    return "\n".join(lines)


def print_stats(stats: CorpusStats) -> None:
    """Print stats report to stdout."""
    print(f"\n{format_stats(stats)}\n")


def _append_optional_summary(lines: list[str], stats: CorpusStats) -> None:
    if stats.get("avg_confidence") is not None:
        lines.append(f"  Avg Konfidenz: {stats['avg_confidence']:.2f}")
    if stats.get("avg_fields_per_doc") is not None:
        lines.append(f"  Avg Fields:    {stats['avg_fields_per_doc']}")

    date_range = stats.get("date_range", {})
    if date_range.get("earliest"):
        lines.append(f"  Zeitraum:      {date_range['earliest']} - {date_range.get('latest', '?')}")


def _append_group_sections(lines: list[str], stats: CorpusStats) -> None:
    for label, key in GROUP_SECTIONS:
        data = stats.get(key, {})
        if not data:
            continue
        lines.extend(["", f"  {label}:"])
        for name, count in sorted(data.items(), key=lambda item: -item[1])[:10]:
            lines.append(f"    {name:30s} {count:>5d}")


def _append_top_sections(lines: list[str], stats: CorpusStats) -> None:
    for label, key in TOP_SECTIONS:
        data = stats.get(key, [])
        if not data:
            continue
        lines.extend(["", f"  {label}:"])
        for name, count in data[:10]:
            lines.append(f"    {name:30s} {count:>5d}")
