"""Review-state helpers for structured pipeline payloads."""

from __future__ import annotations

from typing import Any


def structured_processing_payload(payload: dict) -> dict:
    processing = payload.get("processing", {}) or {}
    return processing if isinstance(processing, dict) else {}


def structured_needs_review(payload: dict) -> bool:
    processing = structured_processing_payload(payload)
    return bool(processing.get("needs_review")) or bool(payload.get("needs_review"))


def structured_review_reason(payload: dict) -> str:
    processing = structured_processing_payload(payload)
    reason = str(processing.get("review_reason", "")).strip()
    return reason or str(payload.get("review_reason", "")).strip()


def payload_needs_review(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    processing = structured_processing_payload(payload)
    return bool(processing.get("needs_review")) or bool(payload.get("needs_review"))


def payload_review_reason(payload: dict) -> str:
    return structured_review_reason(payload if isinstance(payload, dict) else {})


def clear_record_review_state(record: Any) -> None:
    record.review_reason = ""
    record.interpreter_needs_review = False
    record.interpreter_review_reason = ""
    record.validator_needs_review = False
    record.validator_review_reason = ""
    record.normalizer_needs_review = False
    record.normalizer_review_reason = ""


def record_needs_review(record: Any) -> bool:
    return bool(
        getattr(record, "interpreter_needs_review", False)
        or getattr(record, "validator_needs_review", False)
        or getattr(record, "normalizer_needs_review", False)
        or str(getattr(record, "review_reason", "") or "").strip()
    )


def refresh_record_review_reason(record: Any) -> str:
    interpreter_reason = str(getattr(record, "interpreter_review_reason", "") or "").strip()
    validator_reason = str(getattr(record, "validator_review_reason", "") or "").strip()
    normalizer_reason = str(getattr(record, "normalizer_review_reason", "") or "").strip()
    interpreter_active = bool(getattr(record, "interpreter_needs_review", False))
    validator_active = bool(getattr(record, "validator_needs_review", False))
    normalizer_active = bool(getattr(record, "normalizer_needs_review", False))
    active_parts: list[tuple[str, str]] = []
    if interpreter_active:
        active_parts.append(("Interpreter", interpreter_reason or "needs_review"))
    if validator_active:
        active_parts.append(("Validator", validator_reason or "needs_review"))
    if normalizer_active:
        active_parts.append(("Normalizer", normalizer_reason or "needs_review"))
    if not active_parts:
        record.review_reason = ""
        return ""
    if len(active_parts) == 1:
        record.review_reason = active_parts[0][1]
        return record.review_reason
    record.review_reason = " | ".join(f"{label}: {reason}" for label, reason in active_parts)
    return record.review_reason


def mark_record_stage_review(record: Any, *, stage: str, reason: str = "") -> str:
    reason = str(reason or "").strip()
    if stage == "interpreter":
        record.interpreter_needs_review = True
        record.interpreter_review_reason = _merge_review_reason(
            getattr(record, "interpreter_review_reason", ""),
            reason,
        )
    elif stage == "validator":
        record.validator_needs_review = True
        record.validator_review_reason = _merge_review_reason(
            getattr(record, "validator_review_reason", ""),
            reason,
        )
    elif stage == "normalizer":
        record.normalizer_needs_review = True
        record.normalizer_review_reason = _merge_review_reason(
            getattr(record, "normalizer_review_reason", ""),
            reason,
        )
    else:
        raise ValueError(f"Unknown review stage: {stage!r}")
    return refresh_record_review_reason(record)


def normalizer_failure_reason(normalization: Any) -> str:
    if normalization.status != "OK":
        return normalization.error or normalization.message or "Unknown error"
    return ""


def _merge_review_reason(existing: str, new_reason: str) -> str:
    parts = [part.strip() for part in str(existing or "").split(" | ") if part.strip()]
    candidate = str(new_reason or "").strip()
    if candidate and candidate not in parts:
        parts.append(candidate)
    return " | ".join(parts)
