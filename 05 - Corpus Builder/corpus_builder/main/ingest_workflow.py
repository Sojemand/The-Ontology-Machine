"""Workflow stages for CLI ingest and rebuild commands."""
from __future__ import annotations

from types import SimpleNamespace


def run_load(args, *, context, seams: SimpleNamespace) -> None:
    input_path = context.resolve_path(args.input)
    corpus_db = seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None))

    if input_path.is_dir():
        raise SystemExit(
            "Ordner-Eingaben laufen ueber 'rebuild' oder den Orchestrator Debug Host, nicht ueber 'load'."
        )
    if not input_path.name.endswith(".structured.normalized.json"):
        raise SystemExit("Eingabe muss *.structured.normalized.json sein.")

    structured_path = (
        context.resolve_path(args.structured_evidence)
        if getattr(args, "structured_evidence", None)
        else None
    )
    raw_path = context.resolve_path(args.raw_evidence) if getattr(args, "raw_evidence", None) else None
    validation_path = context.resolve_path(args.validation_report) if args.validation_report else None
    if structured_path is None and validation_path is not None:
        raise SystemExit("--validation-report darf nur zusammen mit --structured-evidence gesetzt sein.")
    if structured_path is not None and validation_path is None:
        raise SystemExit("--validation-report ist fuer --structured-evidence Pflicht.")

    bundles = [
        seams.build_load_bundle(
            context,
            normalized_path=input_path,
            structured_path=structured_path,
            validation_path=validation_path,
            raw_path=raw_path,
            corpus_db_path=corpus_db,
        )
    ]

    result = seams.load_batch(context, bundles)
    for bundle, item in zip(bundles, result.results):
        suffix = f" ({item.reason})" if item.reason else ""
        label_path = bundle.normalized_path or bundle.structured_path
        label = label_path.name if label_path is not None else "<unbekannt>"
        print(f"  {label}: {item.status}{suffix}")

    print(
        f"\nGeladen: {result.loaded}, Uebersprungen: {result.skipped}, "
        f"Archiviert: {result.archived}, Fehler: {result.errors}"
    )


def run_rebuild(args, *, context, seams: SimpleNamespace) -> None:
    preview = seams.build_rebuild_bundles_from_artifacts(
        context,
        pipeline_root=getattr(args, "pipeline_root", None),
        normalized_dir=getattr(args, "normalized_dir", None),
        structured_dir=getattr(args, "structured_dir", None),
        validation_dir=getattr(args, "validation_dir", None),
        raw_dir=getattr(args, "raw_dir", None),
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )

    artifact_roots = preview.get("artifact_roots") or []
    if artifact_roots:
        print("Artefakt-Cluster:")
        for root in artifact_roots:
            print(f"  - {root}")

    _print_preview_dirs(preview, "normalized_dirs", "normalized_dir", "Normalized")
    _print_preview_dirs(preview, "structured_dirs", "structured_dir", "Structured")
    _print_preview_dirs(preview, "validation_dirs", "validation_dir", "Validation")
    print(
        f"Artefakte: {preview['bundle_count']} normalized, "
        f"{preview['missing_structured_count']} ohne structured, "
        f"{preview['missing_validation_count']} ohne validation"
    )

    rebuilt = seams.rebuild_corpus_from_artifacts(
        context,
        pipeline_root=getattr(args, "pipeline_root", None),
        normalized_dir=getattr(args, "normalized_dir", None),
        structured_dir=getattr(args, "structured_dir", None),
        validation_dir=getattr(args, "validation_dir", None),
        raw_dir=getattr(args, "raw_dir", None),
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
        replace_existing=not bool(getattr(args, "keep_existing", False)),
    )
    batch = rebuilt["result"]
    print(
        f"Aktiver Release: {rebuilt['active_release_id']} {rebuilt['active_release_version']} "
        f"({rebuilt['active_release_path']})"
    )
    print(f"Corpus DB: {rebuilt['corpus_db_path']}")
    print(
        f"Neu aufgebaut: {batch.loaded} geladen, {batch.skipped} uebersprungen, "
        f"{batch.archived} archiviert, {batch.errors} Fehler"
    )


def _print_preview_dirs(preview: dict, plural_key: str, singular_key: str, label: str) -> None:
    values = list(preview.get(plural_key) or [])
    if not values and preview.get(singular_key):
        values.append(preview[singular_key])
    for value in values:
        print(f"{label}: {value}")


__all__ = ["run_load", "run_rebuild"]
