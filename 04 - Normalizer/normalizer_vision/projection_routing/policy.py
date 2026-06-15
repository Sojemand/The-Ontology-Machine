"""Pure scoring and hint parsing rules for projection routing."""
from __future__ import annotations

from typing import Any

from ..models.coercion import coerce_float
from ..taxonomy import TaxonomyProfile
from .config import default_routing_settings
from .surface_signals import score_surface_signals
from .types import ProjectionHint


def extract_projection_hint(raw_doc: dict[str, Any]) -> ProjectionHint:
    context = raw_doc.get("context")
    if not isinstance(context, dict):
        return ProjectionHint(None, None, None, [])
    hint = context.get("projection_hint")
    if not isinstance(hint, dict):
        return ProjectionHint(None, None, None, [])
    projection_id = _coerce_text(hint.get("projection_id"))
    reason = _coerce_text(hint.get("reason"))
    matched_signals = [text for text in (_coerce_text(item) for item in hint.get("matched_signals", [])) if text]
    confidence = coerce_float(hint.get("confidence"), 0.0)
    return ProjectionHint(projection_id, confidence, reason, matched_signals)


def score_profile(
    profile: TaxonomyProfile,
    raw_doc: dict[str, Any],
    routing_settings: dict[str, int | float] | None = None,
) -> tuple[int, list[str]]:
    settings = routing_settings or default_routing_settings()
    raw_classification = raw_doc.get("classification") if isinstance(raw_doc.get("classification"), dict) else {}
    content = raw_doc.get("content") if isinstance(raw_doc.get("content"), dict) else {}
    structure = content.get("structure") if isinstance(content.get("structure"), dict) else {}
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []

    score = 0
    signals: list[str] = []
    for kind, raw_value, weight in (
        ("document_type", raw_classification.get("document_type"), 6),
        ("category", raw_classification.get("category"), 4),
        ("subcategory", raw_classification.get("subcategory"), 5),
    ):
        canonical = profile.canonical_code(kind, raw_value, None)
        if canonical and canonical != "other":
            score += weight
            signals.append(f"{kind}:{canonical}")

    score += _score_aliases(
        profile,
        "field",
        list(fields.keys()) + _scalar_keys(structure.get("form_fields")),
        signals,
        settings["field_signal_limit"],
    )
    score += _score_aliases(
        profile,
        "row",
        [_coerce_text(row.get("_row_type")) for row in rows if isinstance(row, dict)],
        signals,
        settings["row_signal_limit"],
    )
    cell_keys = _scalar_keys(structure.get("columns")) + [
        key
        for row in rows
        if isinstance(row, dict)
        for key in row.keys()
        if not str(key).startswith("_")
    ]
    score += _score_aliases(profile, "cell", cell_keys, signals, settings["cell_signal_limit"])
    surface_score, surface_hits = score_surface_signals(profile, raw_doc)
    score += surface_score
    signals.extend(surface_hits)
    return score, signals


def format_signal_summary(signals: list[str], *, limit: int = 6) -> str:
    return ", ".join(signals[:limit]) if signals else "no reliable signals"


def _score_aliases(
    profile: TaxonomyProfile,
    kind: str,
    raw_values: list[str | None],
    signals: list[str],
    limit: int,
) -> int:
    seen: set[str] = set()
    for raw_value in raw_values:
        canonical = profile.canonical_code(kind, raw_value, None)
        if canonical is None or canonical == "other" or canonical in seen:
            continue
        seen.add(canonical)
        signals.append(f"{kind}:{canonical}")
        if len(seen) >= limit:
            break
    return len(seen)


def _scalar_keys(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        text = _coerce_text(value)
        if text:
            result.append(text)
    return result


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
