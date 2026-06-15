from __future__ import annotations

import re
from typing import Any

TECHNICAL_HINT_KEYS = frozenset({
    "mode", "prompt_strategy", "section_count", "optimizer_profile", "interpreter_profile", "vision_mode",
    "document_page_count", "page_image_count", "raw_extract_count", "chars_returned", "truncated", "inspection_id",
    "inspection_folder", "input_copy_path", "source_document_path", "sample_label", "filename", "extension", "size_bytes",
})
TECHNICAL_HINT_VALUES = frozenset({"file", "vision", "single", "vision grouped sections", "vision grouped section", "vision grouped", "file text", "optimizer", "interpreter"})
LOW_VALUE_MARKERS = frozenset("""
about after again also asked because been before being between could didn does doesn don don't document from have into just know like more
name page said same shall some story than that them then there these they think this though three through what when where which with would
""".split())


def document_concepts(sample: dict[str, Any]) -> dict[str, list[str]]:
    hints = sample.get("content_hints") if isinstance(sample.get("content_hints"), dict) else {}
    signals = sample.get("signals") if isinstance(sample.get("signals"), dict) else {}
    field_like, ignored = split_semantic_and_technical_hints(flatten_text(hints.get("field_like_phrases")))
    raw_markers = [*flatten_text(hints.get("candidate_markers")), *flatten_text(sample.get("candidate_markers")), *flatten_text(signals.get("estimated_document_type"))]
    return {
        "headings": limit_unique([item for item in flatten_text(hints.get("headings")) if is_semantic_phrase(item)], limit=20),
        "field_like_phrases": limit_unique(field_like, limit=30),
        "candidate_markers": limit_unique([item for item in raw_markers if is_semantic_marker(item)], limit=30),
        "ignored_technical_hints": limit_unique(ignored, limit=30),
    }


def observed_field_evidence(concepts: dict[str, list[str]]) -> list[str]:
    return limit_unique([*concepts.get("field_like_phrases", []), *concepts.get("headings", [])], limit=30)


def candidate_field_labels(unsupported_fields: list[str], observed_fields: list[str]) -> list[str]:
    labels = [field_label(item) for item in [*unsupported_fields, *observed_fields[:8]]]
    return limit_unique([label for label in labels if label and is_semantic_phrase(label)], limit=12)


def source_sample_summary(sample: dict[str, Any], concepts: dict[str, list[str]]) -> dict[str, Any]:
    signals = sample.get("signals") if isinstance(sample.get("signals"), dict) else {}
    excerpt = sample.get("excerpt") if isinstance(sample.get("excerpt"), dict) else {}
    signal_summary = {
        "filename": str(signals.get("filename") or ""),
        "extension": str(signals.get("extension") or ""),
        "detected_language": str(signals.get("detected_language") or ""),
        "estimated_document_type": str(signals.get("estimated_document_type") or ""),
    }
    if signals.get("document_page_count") is not None:
        signal_summary["document_page_count"] = signals.get("document_page_count")
    return {
        "status": sample.get("status", ""),
        "source_document_path": str(sample.get("source_document_path") or ""),
        "sample_label": str(sample.get("sample_label") or ""),
        "signals": signal_summary,
        "content_hints": {
            "headings": concepts.get("headings", []),
            "field_like_phrases": concepts.get("field_like_phrases", []),
            "candidate_markers": concepts.get("candidate_markers", []),
            "ignored_technical_hints": concepts.get("ignored_technical_hints", []),
        },
        "excerpt": {"chars_returned": excerpt.get("chars_returned", 0), "truncated": bool(excerpt.get("truncated", False)), "chunks": limit_unique(flatten_text(excerpt.get("chunks")), limit=4)},
        "workflow_guidance": [
            "Use semantic document content for archive-rule refinement.",
            "Do not propose processing metadata as user-facing archive fields.",
            "Field evidence is not a final taxonomy proposal; the Agent must formulate user-facing fields from evidence and product context.",
        ],
    }


def split_semantic_and_technical_hints(values: list[str]) -> tuple[list[str], list[str]]:
    semantic, technical = [], []
    for value in values:
        text = str(value or "").strip()
        if text and is_technical_hint(text):
            technical.append(text)
        elif text and is_semantic_phrase(text):
            semantic.append(text)
    return semantic, technical


def is_semantic_phrase(value: str) -> bool:
    text = str(value or "").strip()
    if not text or is_technical_hint(text):
        return False
    normalized = norm(text)
    if not normalized or normalized in LOW_VALUE_MARKERS or normalized in TECHNICAL_HINT_VALUES:
        return False
    tokens = normalized.split()
    return not (len(tokens) == 1 and tokens[0] in LOW_VALUE_MARKERS) and any(len(token) >= 4 and token not in LOW_VALUE_MARKERS for token in tokens)


def is_semantic_marker(value: str) -> bool:
    return is_semantic_phrase(value) and norm(value) not in TECHNICAL_HINT_VALUES


def is_technical_hint(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    key = text.split(":", 1)[0].strip().casefold().replace("-", "_").replace(" ", "_")
    value_part = text.split(":", 1)[1].strip() if ":" in text else ""
    normalized_value = norm(value_part or text)
    return key in TECHNICAL_HINT_KEYS or key.endswith(("_profile", "_path", "_count", "_id")) or normalized_value in TECHNICAL_HINT_VALUES


def unsupported(values: list[str], release_terms: set[str], *, limit: int) -> list[str]:
    return limit_unique([text for text in (str(value or "").strip() for value in values) if text and not concept_supported(text, release_terms)], limit=limit)


def concept_supported(value: str, release_terms: set[str]) -> bool:
    normalized = norm(value)
    if not normalized or normalized in release_terms:
        return True
    concept_tokens = {token for token in normalized.split() if len(token) >= 4}
    release_tokens = {token for term in release_terms for token in term.split() if len(token) >= 4}
    return not concept_tokens or bool(concept_tokens & release_tokens)


def normalized_terms(values: list[str]) -> set[str]:
    return {norm(item) for item in values if norm(item)}


def field_label(value: str) -> str:
    text = str(value or "").strip().split(":", 1)[0]
    return re.sub(r"\s+", " ", text).strip(" -_\t")[:80]


def norm(value: str) -> str:
    text = str(value or "").casefold().replace("ÃƒÅ¸", "ss")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def limit_unique(values: list[str], *, limit: int) -> list[str]:
    result, seen = [], set()
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            result.append(text[:160])
        if len(result) >= limit:
            break
    return result


def compact_text(value: Any) -> str:
    return " ".join(flatten_text(value))[:20000]


def flatten_text(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in flatten_text(item)]
    if isinstance(value, list):
        return [text for item in value for text in flatten_text(item)]
    return [str(value)]


__all__ = [name for name in globals() if not name.startswith("__")]
