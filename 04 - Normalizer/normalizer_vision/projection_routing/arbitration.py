"""Shared advisory hint-arbitration helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .types import ProjectionHint

_SEPARATOR_RE = re.compile(r"[\s:._\-/]+")


@dataclass(frozen=True, slots=True)
class AdvisoryDecision:
    projection_id: str
    mode: str
    reason: str


def select_advisory_projection(
    *,
    scores: dict[str, tuple[int, list[str]]],
    fallback_projection_id: str,
    hint: ProjectionHint,
    routing_settings: dict[str, int | float],
) -> AdvisoryDecision:
    best_local_id, best_local_score, best_local_signals = _best_profile(scores, fallback_projection_id)
    if hint.projection_id not in scores:
        return AdvisoryDecision(
            projection_id=fallback_projection_id,
            mode="hint_rejected",
            reason=(
                f"Interpreter hint {hint.projection_id} rejected: projection is unknown in the local catalog; "
                f"confidence={_format_confidence(hint.confidence)} => confidence_bonus=0; "
                f"verified_hint_signals=0/{routing_settings['matched_signal_bonus_cap']} [none]; "
                f"best_local={best_local_id} local_score={best_local_score} "
                f"[{_format_signals(best_local_signals)}]; fallback={fallback_projection_id} remains active."
            ),
        )
    hint_local_score, hint_local_signals = scores[hint.projection_id]
    confidence_bonus = _confidence_bonus(hint.confidence, routing_settings)
    verified_signals = _verified_hint_signals(hint.matched_signals, hint_local_signals)
    signal_bonus_cap = int(routing_settings["matched_signal_bonus_cap"])
    signal_bonus = min(len(verified_signals), signal_bonus_cap)
    adjusted_hint_score = hint_local_score + confidence_bonus + signal_bonus
    challenger_id, challenger_score, challenger_signals = _best_profile(
        {key: value for key, value in scores.items() if key != hint.projection_id},
        fallback_projection_id,
    )
    margin = int(routing_settings["hint_reject_margin"])
    delta = challenger_score - adjusted_hint_score
    base_reason = (
        f"hint={hint.projection_id} local_score={hint_local_score}; "
        f"confidence={_format_confidence(hint.confidence)} => confidence_bonus={confidence_bonus}; "
        f"verified_hint_signals={signal_bonus}/{signal_bonus_cap} [{_format_values(verified_signals)}]; "
        f"adjusted_hint_score={adjusted_hint_score}; "
        f"best_challenger={challenger_id} local_score={challenger_score} "
        f"[{_format_signals(challenger_signals)}]; "
        f"reject_margin={margin}; challenger_delta={delta}."
    )
    if delta >= margin:
        return AdvisoryDecision(
            projection_id=challenger_id,
            mode="hint_rejected",
            reason=f"Interpreter hint {hint.projection_id} rejected: {base_reason}",
        )
    return AdvisoryDecision(
        projection_id=hint.projection_id,
        mode="hint_validated",
        reason=f"Interpreter hint {hint.projection_id} accepted: {base_reason}",
    )


def _best_profile(
    scores: dict[str, tuple[int, list[str]]],
    fallback_projection_id: str,
) -> tuple[str, int, list[str]]:
    if not scores:
        return fallback_projection_id, 0, []
    ranked = sorted(
        scores.items(),
        key=lambda item: (-item[1][0], item[0] != fallback_projection_id, item[0]),
    )
    projection_id, (score, signals) = ranked[0]
    return projection_id, score, signals


def _confidence_bonus(confidence: float | None, routing_settings: dict[str, int | float]) -> int:
    candidate = float(confidence or 0.0)
    if candidate >= float(routing_settings["hint_confidence_high_threshold"]):
        return int(routing_settings["hint_confidence_high_bonus"])
    if candidate >= float(routing_settings["hint_confidence_medium_threshold"]):
        return int(routing_settings["hint_confidence_medium_bonus"])
    if candidate >= float(routing_settings["hint_confidence_low_threshold"]):
        return int(routing_settings["hint_confidence_low_bonus"])
    return 0


def _verified_hint_signals(hint_signals: list[str], local_signals: list[str]) -> list[str]:
    normalized_local = [_normalize_signal(signal) for signal in local_signals]
    verified: list[str] = []
    seen: set[str] = set()
    for raw_signal in hint_signals:
        normalized_hint = _normalize_signal(raw_signal)
        if not normalized_hint or normalized_hint in seen:
            continue
        if any(local == normalized_hint or local.endswith(f" {normalized_hint}") for local in normalized_local):
            seen.add(normalized_hint)
            verified.append(normalized_hint)
    return verified


def _normalize_signal(value: str | None) -> str:
    return _SEPARATOR_RE.sub(" ", str(value or "").strip().casefold()).strip()


def _format_confidence(confidence: float | None) -> str:
    return f"{float(confidence or 0.0):.2f}"


def _format_signals(signals: list[str], *, limit: int = 6) -> str:
    return _format_values(signals[:limit]) if signals else "none"


def _format_values(values: list[str]) -> str:
    return ", ".join(values) if values else "none"
