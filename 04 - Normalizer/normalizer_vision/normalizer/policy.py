"""Soft normalization policy for model outputs and review heuristics."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ..models.coercion import coerce_string as base_coerce_string
from ..models.coercion import dedupe_keep_order, string_list as base_string_list
from ..models.serialization import to_json_compatible

PAYMENT_SCHEDULE_TAX_HINT_RE = re.compile(r"\b(umsatzsteuer|vat|mwst)\b", re.IGNORECASE)
REVIEW_TRIGGER_PATTERNS = (
    re.compile(r"\bdropped unknown\b", re.IGNORECASE),
    re.compile(r"\bunknown\b", re.IGNORECASE),
    re.compile(r"\bunbekannt\b", re.IGNORECASE),
    re.compile(r"\bunsicher\b", re.IGNORECASE),
    re.compile(r"\buncertain\b", re.IGNORECASE),
    re.compile(r"\bkonnte nicht\b", re.IGNORECASE),
    re.compile(r"\bcould not\b", re.IGNORECASE),
    re.compile(r"\bseriali[sz]\w*\b", re.IGNORECASE),
    re.compile(r"\bauf 'other'\b", re.IGNORECASE),
    re.compile(r"\bto 'other'\b", re.IGNORECASE),
    re.compile(r"\breview\b", re.IGNORECASE),
)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[T\s]")
FREE_TEXT_DATE_RE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b")


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return stripped


def coerce_string(value: Any) -> str | None:
    return base_coerce_string(value, normalize=repair_mojibake_text)


def is_empty_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, dict):
        return all(is_empty_placeholder(child) for child in value.values())
    return False


def string_list(value: Any) -> list[str]:
    return base_string_list(value, normalize=repair_mojibake_text)


def string_list_with_fallback(primary: Any, fallback: Any) -> list[str]:
    values = dedupe_keep_order(string_list(primary))
    return values if values else dedupe_keep_order(string_list(fallback))


def numeric_with_fallback(primary: Any, fallback: Any) -> int | float | None:
    if isinstance(primary, (int, float)) and not isinstance(primary, bool):
        return primary
    if isinstance(fallback, (int, float)) and not isinstance(fallback, bool):
        return fallback
    return None


def flatten_tokens(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        tokens: list[str] = []
        for key, child in value.items():
            tokens.append(str(key))
            tokens.extend(flatten_tokens(child))
        return tokens
    if isinstance(value, list):
        tokens: list[str] = []
        for child in value:
            tokens.extend(flatten_tokens(child))
        return tokens
    return [str(value)]


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_iso_date(value: Any) -> Any:
    text = coerce_string(value)
    if text is None:
        return value
    if ISO_DATE_RE.fullmatch(text):
        return text
    iso_prefix_match = ISO_DATETIME_PREFIX_RE.match(text)
    if iso_prefix_match:
        return iso_prefix_match.group(1)
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def repair_mojibake_text(text: str) -> str:
    current = text
    for _ in range(2):
        if _mojibake_score(current) == 0:
            break
        best = current
        best_score = _mojibake_score(current)
        for encoding in ("cp1252", "latin-1"):
            try:
                candidate = current.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if _contains_control_chars(candidate):
                continue
            candidate_score = _mojibake_score(candidate)
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score
        if best == current:
            break
        current = best
    return current


def normalize_output_value(value: Any) -> Any:
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, list):
        return [normalize_output_value(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_output_value(child) for key, child in value.items()}
    return to_json_compatible(value)


def normalize_dates_in_text(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        normalized = normalize_iso_date(match.group(0))
        return normalized if isinstance(normalized, str) else match.group(0)

    return FREE_TEXT_DATE_RE.sub(replace, text)


def has_tax_split_hint(row: dict[str, Any]) -> bool:
    percentage_share = coerce_string(row.get("percentage_share"))
    if percentage_share:
        return True
    return bool(PAYMENT_SCHEDULE_TAX_HINT_RE.search(coerce_string(row.get("other")) or ""))


def notes_require_review(notes: list[str]) -> bool:
    return any(any(pattern.search(note) for pattern in REVIEW_TRIGGER_PATTERNS) for note in notes)


def classification_requires_review(classification: dict[str, Any]) -> bool:
    return any(classification.get(key) == "other" for key in ("document_type", "category"))


def derive_review_reason(
    explicit_needs_review: bool,
    review_reason: str | None,
    classification: dict[str, Any],
    notes: list[str],
) -> str | None:
    explicit = coerce_string(review_reason)
    if explicit:
        return explicit
    reasons: list[str] = []
    other_keys = [key for key in ("document_type", "category") if classification.get(key) == "other"]
    if other_keys:
        reasons.append(f"Unklare Klassifikation: {', '.join(other_keys)} wurde auf other gesetzt.")
    note_reason = next(
        (
            note.strip()
            for note in notes
            if any(pattern.search(note) for pattern in REVIEW_TRIGGER_PATTERNS) and note.strip()
        ),
        None,
    )
    if note_reason:
        reasons.append(note_reason)
    if not reasons and explicit_needs_review:
        reasons.append("Modell markierte needs_review; die Normalisierung muss manuell geprueft werden.")
    return " ".join(dedupe_keep_order(reasons)) or None


def _mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in ("Ã", "Â", "â", "ï¿½"))


def _contains_control_chars(text: str) -> bool:
    return any(ord(char) < 32 and char not in "\t\r\n" for char in text)
