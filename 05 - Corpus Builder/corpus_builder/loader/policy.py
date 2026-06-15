"""Soft rules, normalization and candidate heuristics for the loader."""
from __future__ import annotations
import re
import unicodedata
from typing import Any
from .types import JsonDict

_DATE_PATTERNS = (re.compile(r"\d{4}-\d{2}-\d{2}$"), re.compile(r"\d{2}\.\d{2}\.\d{4}$"), re.compile(r"\d{2}/\d{2}/\d{4}$"))
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CURRENCY_SYMBOL_PATTERN = re.compile(r"(?:\u20ac|\u00a3|\$|EUR|GBP)")

def is_non_empty(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip())) and (not isinstance(value, (list, dict)) or bool(value))
def normalize_search_text(value: Any) -> str | None:
    if not is_non_empty(value):
        return None
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[_./\\-]+", " ", text)).strip() or None
def compact_search_text(value: Any) -> str | None:
    normalized = normalize_search_text(value)
    return re.sub(r"[^0-9a-z]+", "", normalized) or None if normalized else None
def _strip_sign_tokens(value: str) -> tuple[str, bool]:
    text, negative = value.strip().replace("\u00a0", " "), False
    if text.startswith("(") and text.endswith(")"):
        text, negative = text[1:-1].strip(), True
    if text.startswith("-"):
        text, negative = text[1:].strip(), True
    elif text.startswith("+"):
        text = text[1:].strip()
    return text.strip(), negative
def _normalize_numeric_string(value: str) -> str | None:
    text = value.replace(" ", "")
    if not text or not re.fullmatch(r"[\d.,]+", text):
        return None
    if "." in text and "," in text:
        decimal_sep = "." if text.rfind(".") > text.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        integer_part, fractional_part = text.rsplit(decimal_sep, 1)
        groups = integer_part.split(thousands_sep)
        if not fractional_part or len(fractional_part) not in {1, 2} or thousands_sep in fractional_part or any(not item.isdigit() for item in groups) or any(len(item) != 3 for item in groups[1:]):
            return None
        return "".join(groups) + "." + fractional_part
    for sep in (".", ","):
        if sep not in text:
            continue
        groups = text.split(sep)
        if any(not item.isdigit() for item in groups):
            return None
        if len(groups) == 2:
            return groups[0] + "." + groups[1] if groups[0] and len(groups[1]) in {1, 2} else None
        return "".join(groups) if all(len(item) == 3 for item in groups[1:]) else None
    return text if text.isdigit() else None
def _parse_numeric_string(value: str, *, allow_currency: bool = False) -> float | None:
    text, negative = _strip_sign_tokens(value)
    normalized = _normalize_numeric_string(_CURRENCY_SYMBOL_PATTERN.sub("", text).strip() if allow_currency else text)
    if normalized is None:
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    return -parsed if negative else parsed
def detect_field_type(_key: str, value: Any) -> tuple[str, float | None]:
    if isinstance(value, bool):
        return ("text", None)
    if isinstance(value, (int, float)):
        return ("number", float(value))
    if isinstance(value, (dict, list)):
        return ("json", None)
    if not isinstance(value, str):
        return ("text", None)
    stripped = value.strip()
    if any(pattern.match(stripped) for pattern in _DATE_PATTERNS):
        return ("date", None)
    if _CURRENCY_SYMBOL_PATTERN.search(stripped):
        parsed = _parse_numeric_string(stripped, allow_currency=True)
        if parsed is not None:
            return ("currency", parsed)
    parsed = _parse_numeric_string(stripped)
    return ("number", parsed) if parsed is not None else ("text", None)
def normalize_date_value(value: Any) -> str | None:
    text = "" if value is None or isinstance(value, (int, float, bool)) else str(value).strip()
    if not text:
        return None
    if _ISO_DATE_PATTERN.fullmatch(text):
        return text
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", text):
        day, month, year = text.split(".")
        return f"{year}-{month}-{day}"
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        month, day, year = text.split("/")
        return f"{year}-{month}-{day}"
    return None
def extract_currency(value: Any) -> str | None:
    text = "" if value is None else str(value)
    return "EUR" if "\u20ac" in text or "EUR" in text else "GBP" if "\u00a3" in text or "GBP" in text else "USD" if "$" in text else None
def normalize_source_refs(value: Any) -> list[str]:
    return [value] if isinstance(value, str) else [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
def _candidate_payload(slot: str, value: Any, *, strategy: str, confidence: float | None, source_refs: list[str] | None = None, evidence_paths: list[str] | None = None, ambiguity_group: str | None = None, is_projection_backed: bool = False, origin_path: str | None = None, origin_kind: str | None = None, candidate_layer: str = "base", candidate_origin: str | None = None) -> JsonDict | None:
    if not is_non_empty(value):
        return None
    value_type, numeric_value = detect_field_type(slot, value)
    display_value = str(value).strip()
    return {"slot": slot, "display_value": display_value, "normalized_value": normalize_search_text(display_value), "compact_value": compact_search_text(display_value), "numeric_value": numeric_value, "date_value": normalize_date_value(value) if value_type == "date" or isinstance(value, str) else None, "strategy": strategy, "confidence": confidence, "ambiguity_group": ambiguity_group or slot, "is_projection_backed": int(is_projection_backed), "candidate_layer": candidate_layer or "base", "candidate_origin": candidate_origin or origin_kind or strategy, "source_refs": list(dict.fromkeys(source_refs or [])), "origin_path": origin_path, "origin_kind": origin_kind, "evidence_paths": [path for path in (evidence_paths or []) if path]}
def _append_candidate(candidates: list[JsonDict], seen: set[tuple[str, str | None, str | None, str]], slot: str, value: Any, **kwargs: Any) -> None:
    promotion_index = kwargs.pop("promotion_index", None)
    candidate = _candidate_payload(slot, value, **kwargs)
    if candidate is not None:
        if isinstance(promotion_index, int):
            candidate["promotion_index"] = promotion_index
        identity = (candidate["slot"], candidate["normalized_value"], candidate["origin_path"], candidate["strategy"])
        if identity not in seen:
            seen.add(identity)
            candidates.append(candidate)
def _append_projection_entries(candidates: list[JsonDict], seen: set[tuple[str, str | None, str | None, str]], projection: JsonDict) -> None:
    for slot_entry in projection.get("slots") or []:
        if isinstance(slot_entry, dict):
            _append_candidate(candidates, seen, str(slot_entry.get("slot") or "unknown"), slot_entry.get("primary_value"), strategy=f"projection_slot:{slot_entry.get('status') or 'unknown'}", confidence=1.0 if slot_entry.get("status") == "resolved" else 0.6, source_refs=normalize_source_refs(slot_entry.get("source_refs")), evidence_paths=[str(slot_entry.get("primary_path") or "")], ambiguity_group=str(slot_entry.get("slot") or "projection"), is_projection_backed=True, origin_path=str(slot_entry.get("primary_path") or "") or None, origin_kind="projection_slot", candidate_layer="release", candidate_origin="projection_slot")
    for candidate in projection.get("candidates") or []:
        if isinstance(candidate, dict):
            _append_candidate(candidates, seen, str(candidate.get("slot") or "unknown"), candidate.get("value"), strategy=f"projection_candidate:{candidate.get('origin_kind') or 'unknown'}", confidence=float(candidate.get("rank")) if candidate.get("rank") is not None else None, source_refs=normalize_source_refs(candidate.get("source_refs")), evidence_paths=[str(candidate.get("origin_path") or "")], ambiguity_group=str(candidate.get("slot") or "unknown"), is_projection_backed=True, origin_path=str(candidate.get("origin_path") or "") or None, origin_kind=str(candidate.get("origin_kind") or "projection_candidate"), candidate_layer="release", candidate_origin="projection_candidate")
def build_slot_candidates(payload: JsonDict, _doc: JsonDict, fields: JsonDict, rows: list[JsonDict], tags: list[str], people: list[str], orgs: list[str], *, seed_candidates: list[JsonDict] | None = None) -> list[JsonDict]:
    candidates, seen = [], set()
    for item in seed_candidates or []:
        if isinstance(item, dict):
            _append_candidate(candidates, seen, str(item.get("slot") or "unknown"), item.get("display_value"), strategy=str(item.get("strategy") or "release_promotion"), confidence=float(item.get("confidence")) if item.get("confidence") is not None else None, source_refs=normalize_source_refs(item.get("source_refs")), evidence_paths=[path for path in item.get("evidence_paths") or [] if isinstance(path, str)], ambiguity_group=str(item.get("ambiguity_group") or item.get("slot") or "unknown"), is_projection_backed=bool(item.get("is_projection_backed", 1)), origin_path=str(item.get("origin_path") or "") or None, origin_kind=str(item.get("origin_kind") or "release_rule"), candidate_layer=str(item.get("candidate_layer") or "release"), candidate_origin=str(item.get("candidate_origin") or item.get("origin_kind") or "release_seed"), promotion_index=item.get("promotion_index"))
    projection = payload.get("projection")
    if isinstance(projection, dict):
        _append_projection_entries(candidates, seen, projection)
    for list_name, items, slot, confidence in (("people", people, "person", 0.75), ("organizations", orgs, "organization", 0.75), ("tags", tags, "tag", 0.70)):
        for index, item in enumerate(items):
            _append_candidate(candidates, seen, slot, item, strategy="context_list", confidence=confidence, evidence_paths=[f"context.{list_name}[{index}]"], ambiguity_group=slot, origin_path=f"context.{list_name}[{index}]", origin_kind="context", candidate_layer="base", candidate_origin="context_list")
    return candidates
__all__ = ["build_slot_candidates", "compact_search_text", "detect_field_type", "extract_currency", "is_non_empty", "normalize_date_value", "normalize_search_text", "normalize_source_refs"]
