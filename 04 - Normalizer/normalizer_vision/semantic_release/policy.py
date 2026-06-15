"""Pure release policy and analysis helpers."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from ..taxonomy import upgrade_master_taxonomy_v2
from ..taxonomy.validation import ensure_master_required_keys
from .shared_identity import build_release_fingerprint
from .types import SemanticReleasePayload, TaxonomyAnalysisReport

_INVALID_FILE_CHARS_RE = re.compile(r'[<>:"|?*\x00-\x1f]+')
_WINDOWS_FILE_NAME_BUDGET = 255
_WINDOWS_PATH_BUDGET = 259
_RESERVED_WINDOWS_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def semantic_release_file_name(
    release_id: str,
    *,
    release_version: str | None = None,
    runtime_locale: str | None = None,
) -> str:
    segments = [_sanitize_file_segment(release_id) or "semantic_release.default"]
    if release_version:
        segments.append(_sanitize_file_segment(release_version))
    if runtime_locale:
        segments.append(_sanitize_file_segment(runtime_locale))
    return "__".join(segment for segment in segments if segment) + ".json"


def budget_semantic_release_file_name(
    parent: Path,
    release_id: str,
    *,
    release_version: str | None = None,
    runtime_locale: str | None = None,
    path_budget: int = _WINDOWS_PATH_BUDGET,
) -> str:
    preferred = semantic_release_file_name(
        release_id,
        release_version=release_version,
        runtime_locale=runtime_locale,
    )
    if _fits_windows_budget(parent, preferred, path_budget=path_budget):
        return preferred
    digest = hashlib.sha1(preferred.encode("utf-8")).hexdigest()[:8]
    suffix = f".{digest}.json"
    stem = preferred[: -len(".json")].rstrip(" ._-") or "semantic_release"
    max_stem = _WINDOWS_FILE_NAME_BUDGET - len(suffix)
    stem = stem[:max_stem].rstrip(" ._-") or "semantic_release"
    candidate = f"{stem}{suffix}"
    while not _fits_windows_budget(parent, candidate, path_budget=path_budget) and len(stem) > 1:
        stem = stem[:-1].rstrip(" ._-") or "s"
        candidate = f"{stem}{suffix}"
    if not _fits_windows_budget(parent, candidate, path_budget=path_budget):
        raise ValueError(f"Semantic-Release-Ausgabepfad waere zu lang fuer Windows-Pfadbudget ({path_budget} Zeichen): {Path(parent) / preferred}")
    return candidate


def _sanitize_file_segment(value: Any) -> str:
    segment = str(value or "").strip().replace("/", ".").replace("\\", ".")
    segment = re.sub(r"\s+", "_", segment)
    segment = _INVALID_FILE_CHARS_RE.sub("_", segment).strip(" .")
    if segment.upper() in _RESERVED_WINDOWS_NAMES:
        return f"{segment}_release"
    return segment


def _fits_windows_budget(parent: Path, file_name: str, *, path_budget: int) -> bool:
    return len(file_name) <= _WINDOWS_FILE_NAME_BUDGET and len(str(Path(parent) / file_name)) <= path_budget


def analyze_taxonomy_shape(master: dict[str, Any], projections: list[dict[str, Any]]) -> TaxonomyAnalysisReport:
    validated_master = ensure_master_required_keys(
        upgrade_master_taxonomy_v2(master, include_semantic_defaults=False)
    )
    warnings: list[str] = []
    issues: list[str] = []

    if len(projections) <= 1:
        warnings.append("Es existiert derzeit nur ein reales Projection-Profil.")
    if not validated_master.get("entity_types"):
        issues.append("entity_types fehlen im Master.")
    if not validated_master.get("promotion_slots"):
        issues.append("promotion_slots fehlen im Master.")
    if all(not projection.get("extends") for projection in projections):
        warnings.append("Es existiert noch keine Projection-Komposition ueber extends.")
    if all(not projection.get("compatibility") for projection in projections):
        warnings.append("Projection-Kompatibilitaetsmetadaten sind noch duenn.")

    field_count = len(validated_master.get("field_codes", []) or [])
    bound_fields = sum(
        1
        for item in validated_master.get("field_codes", []) or []
        if isinstance(item, dict) and isinstance(item.get("semantic_binding"), dict)
    )

    return {
        "summary": {
            "taxonomy_id": validated_master.get("taxonomy_id"),
            "taxonomy_version": validated_master.get("taxonomy_version"),
            "projection_count": len(projections),
            "field_code_count": field_count,
            "row_type_count": len(validated_master.get("row_types", []) or []),
            "cell_code_count": len(validated_master.get("cell_codes", []) or []),
            "field_binding_coverage": round(bound_fields / field_count, 3) if field_count else 0.0,
        },
        "suitability": {
            "entity_model_ready": bool(validated_master.get("entity_types")),
            "projection_growth_ready": bool(projections),
            "on_prem_versioning_ready": bool(validated_master.get("compatibility")),
            "deterministic_materialization_ready": bool(validated_master.get("promotion_slots")),
        },
        "issues": issues,
        "warnings": warnings,
        "recommendations": [
            "Projection files should actively use extends and compatibility metadata.",
            "Promotion rules should remain explicitly versioned per projection.",
            "New domains should grow through projection families instead of special-purpose paths.",
        ],
    }
