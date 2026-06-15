"""CLI workflow stage for command orchestration."""
from __future__ import annotations

from pathlib import Path

from ..semantic_release import analyze_taxonomy_shape, build_semantic_release
from ..semantic_release.adapter import load_local_projection_payloads, load_master_taxonomy_payload
from . import adapter
from .types import AnalyzeTaxonomyCommand, CheckConfigCommand


def _load_normalizer_or_report(config_path: str | None, load_normalizer):
    try:
        return load_normalizer(config_path)
    except Exception as exc:
        adapter.print_config_invalid(str(exc))
        return None


def run_check_config(command: CheckConfigCommand, *, load_normalizer=adapter.load_normalizer) -> int:
    try:
        normalizer = load_normalizer(command.config_path)
    except Exception as exc:
        adapter.print_config_invalid(str(exc))
        return 1

    adapter.print_config_valid(normalizer.profile.projection_id)
    return 0


def run_analyze_taxonomy(command: AnalyzeTaxonomyCommand, *, root: Path) -> int:
    _ = command
    try:
        master = load_master_taxonomy_payload(root)
        projections = load_local_projection_payloads(root)
        report = analyze_taxonomy_shape(master, projections)
        release_preview = build_semantic_release(root)
    except Exception as exc:
        adapter.print_error(str(exc))
        return 1
    adapter.print_taxonomy_analysis(report, release_preview)
    return 0
