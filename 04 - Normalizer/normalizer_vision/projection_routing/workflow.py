"""Workflow stage for advisory projection-profile resolution."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assets import build_local_release_runtime
from ..release_runtime import ReleaseRuntime
from .config import load_routing_settings
from .arbitration import select_advisory_projection
from ..taxonomy import TaxonomyProfile
from .policy import extract_projection_hint, score_profile
from .types import ProjectionSelection


def resolve_projection(
    *,
    project_root: Path,
    fallback_profile: TaxonomyProfile,
    raw_doc: dict[str, Any],
    hint_mode: str,
    release_runtime: ReleaseRuntime | None = None,
) -> ProjectionSelection:
    runtime = release_runtime or build_local_release_runtime(
        project_root,
        preferred_profile_id=fallback_profile.projection_id,
    )
    profiles = _load_profiles(fallback_profile, release_runtime=runtime)
    fallback_profile = profiles.get(fallback_profile.projection_id, fallback_profile)
    catalog_version = runtime.catalog_version
    routing_settings = load_routing_settings(project_root)
    scores = {
        projection_id: score_profile(profile, raw_doc, routing_settings)
        for projection_id, profile in profiles.items()
    }
    hint = extract_projection_hint(raw_doc)

    if hint_mode == "off":
        return ProjectionSelection(
            profile=fallback_profile,
            mode="hint_disabled",
            hint_projection_id=hint.projection_id,
            hint_confidence=hint.confidence,
            catalog_version=catalog_version,
            reason="projection_hint_mode=off; using configured fallback profile.",
        )
    if hint_mode == "strict":
        return _resolve_strict(profiles, fallback_profile, catalog_version, hint)
    if hint.projection_id:
        decision = select_advisory_projection(
            scores=scores,
            fallback_projection_id=fallback_profile.projection_id,
            hint=hint,
            routing_settings=routing_settings,
        )
        return ProjectionSelection(
            profile=profiles.get(decision.projection_id, fallback_profile),
            mode=decision.mode,
            hint_projection_id=hint.projection_id,
            hint_confidence=hint.confidence,
            catalog_version=catalog_version,
            reason=decision.reason,
        )
    return _resolve_advisory_without_hint(
        profiles=profiles,
        fallback_profile=fallback_profile,
        catalog_version=catalog_version,
        scores=scores,
        routing_settings=routing_settings,
    )


def _resolve_strict(
    profiles: dict[str, TaxonomyProfile],
    fallback_profile: TaxonomyProfile,
    catalog_version: str,
    hint,
) -> ProjectionSelection:
    if hint.projection_id and hint.projection_id in profiles:
        return ProjectionSelection(
            profile=profiles[hint.projection_id],
            mode="hint_strict",
            hint_projection_id=hint.projection_id,
            hint_confidence=hint.confidence,
            catalog_version=catalog_version,
            reason="projection_hint_mode=strict; using valid interpreter hint directly.",
        )
    return ProjectionSelection(
        profile=fallback_profile,
        mode="hint_strict_fallback",
        hint_projection_id=hint.projection_id,
        hint_confidence=hint.confidence,
        catalog_version=catalog_version,
        reason="projection_hint_mode=strict, but no valid hint is present; using fallback profile.",
    )


def _load_profiles(fallback_profile: TaxonomyProfile, *, release_runtime: ReleaseRuntime) -> dict[str, TaxonomyProfile]:
    profiles = {fallback_profile.projection_id: fallback_profile}
    for projection_id, profile in release_runtime.profiles.items():
        if projection_id in profiles:
            continue
        profiles[projection_id] = profile
    return profiles


def _resolve_advisory_without_hint(
    *,
    profiles: dict[str, TaxonomyProfile],
    fallback_profile: TaxonomyProfile,
    catalog_version: str,
    scores: dict[str, tuple[int, list[str]]],
    routing_settings: dict[str, int | float],
) -> ProjectionSelection:
    ranked = sorted(
        (
            (projection_id, int(score), list(signals))
            for projection_id, (score, signals) in scores.items()
        ),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    if not ranked:
        return ProjectionSelection(
            profile=fallback_profile,
            mode="fallback",
            hint_projection_id=None,
            hint_confidence=None,
            catalog_version=catalog_version,
            reason="No projection_hint in input and no local routing scores are available; using configured fallback profile.",
        )
    best_projection_id, best_score, best_signals = ranked[0]
    next_score = ranked[1][1] if len(ranked) > 1 else 0
    min_score = int(routing_settings["no_hint_local_min_score"])
    margin = int(routing_settings["no_hint_local_margin"])
    score_delta = best_score - next_score
    best_signal_summary = ", ".join(best_signals[:6]) if best_signals else "no reliable signals"
    if (
        best_projection_id != fallback_profile.projection_id
        and best_score >= min_score
        and score_delta >= margin
    ):
        return ProjectionSelection(
            profile=profiles.get(best_projection_id, fallback_profile),
            mode="local_inferred",
            hint_projection_id=None,
            hint_confidence=None,
            catalog_version=catalog_version,
            reason=(
                "No projection_hint in input; local routing selected "
                f"{best_projection_id}: best_score={best_score}; next_score={next_score}; "
                f"required_min_score={min_score}; required_margin={margin}; signals=[{best_signal_summary}]."
            ),
        )
    return ProjectionSelection(
        profile=fallback_profile,
        mode="fallback",
        hint_projection_id=None,
        hint_confidence=None,
        catalog_version=catalog_version,
        reason=(
            "No projection_hint in input; local routing remains below the release threshold "
            f"(best={best_projection_id} score={best_score}, next_score={next_score}, "
            f"required_min_score={min_score}, required_margin={margin}, delta={score_delta}); "
            f"using configured fallback profile. signals=[{best_signal_summary}]"
        ),
    )
