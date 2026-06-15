"""Deterministic id helpers for source-backed draft authoring."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from . import locale_views
from .review_support import keyword_phrases, normalize_text

_MACHINE_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_PROJECTION_ID_RE = re.compile(r"^[a-z0-9]+(?:[._][a-z0-9]+)*$")
_STOPWORDS = {"document", "draft", "review", "sample"}
_SECTION_HINTS = ("field_codes", "cell_codes", "row_types", "document_types", "categories", "subcategories")


def build_lookup(package: dict[str, Any]) -> dict[str, dict[str, str]]:
    master: dict[str, str] = {}
    glossary: dict[str, str] = {}
    active_locale = locale_views.default_authoring_locale(package)
    for section_id in _SECTION_HINTS:
        for term_id, item in package["master"]["texts"][active_locale].get(section_id, {}).items():
            for raw in (term_id, item.get("label", ""), *(item.get("aliases") or [])):
                token = normalize_text(raw)
                if token:
                    master.setdefault(token, f"{section_id}:{term_id}")
    for english_term, item in locale_views.glossary(package, active_locale).get("glossary", {}).items():
        for raw in (english_term, item.get("canonical", ""), *(item.get("aliases") or [])):
            token = normalize_text(raw)
            if token:
                glossary.setdefault(token, str(english_term))
    return {"master": master, "glossary": glossary}


def existing_term(package: dict[str, Any], lookup: dict[str, dict[str, str]], raw_value: str) -> tuple[str, str] | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    for section_id in _SECTION_HINTS:
        if value in package["master"]["core"].get(section_id, {}):
            return section_id, value
    match = lookup["master"].get(normalize_text(value))
    if not match:
        return None
    section_id, term_id = match.split(":", 1)
    return section_id, term_id


def derive_term_id(package: dict[str, Any], lookup: dict[str, dict[str, str]], section_id: str, phrase: str) -> dict[str, Any]:
    raw = str(phrase or "").strip()
    if _MACHINE_ID_RE.fullmatch(raw):
        return {"term_id": _unique(raw, set(package["master"]["core"][section_id])), "requires_id_review": False, "source": "machine_id"}
    glossary_match = lookup["glossary"].get(normalize_text(raw))
    if glossary_match and _MACHINE_ID_RE.fullmatch(glossary_match):
        return {"term_id": _unique(glossary_match, set(package["master"]["core"][section_id])), "requires_id_review": False, "source": "glossary"}
    slug = _slug(raw)
    candidate = f"candidate_{slug or 'draft'}"
    return {"term_id": _unique(candidate, set(package["master"]["core"][section_id])), "requires_id_review": True, "source": "candidate"}


def derive_projection_id(package: dict[str, Any], lookup: dict[str, dict[str, str]], text: str, source_projection_id: str) -> dict[str, Any]:
    seeds = []
    for phrase in keyword_phrases(text):
        existing = lookup["glossary"].get(normalize_text(phrase))
        if existing and _MACHINE_ID_RE.fullmatch(existing):
            seeds.append(existing)
    prefix = str(source_projection_id.split(".", 1)[0] or "candidate")
    if seeds:
        slug = "_".join(_slug(seed) for seed in seeds[:2] if _slug(seed))
        proposal = f"{prefix}.{slug or 'draft'}.default.v1"
        return {"projection_id": _unique_projection_id(package, proposal), "requires_id_review": False}
    slug = _slug(text)
    return {"projection_id": _unique_projection_id(package, f"candidate.{slug or 'draft'}.default.v1"), "requires_id_review": True}


def projection_id_hint(raw_value: str) -> dict[str, Any]:
    value = str(raw_value or "").strip()
    if value and _PROJECTION_ID_RE.fullmatch(value):
        return {"projection_id": value, "requires_id_review": False}
    slug = _slug(value)
    return {"projection_id": f"candidate.{slug or 'draft'}.default.v1", "requires_id_review": True}


def _slug(value: str) -> str:
    text = _ascii_fold(value)
    tokens = [token for token in re.findall(r"[a-z0-9]+", text) if len(token) > 2 and token not in _STOPWORDS]
    return "_".join(tokens[:4])


def _ascii_fold(value: str) -> str:
    folded = unicodedata.normalize("NFKD", str(value or ""))
    return folded.encode("ascii", "ignore").decode("ascii").casefold()


def _unique_projection_id(package: dict[str, Any], proposal: str) -> str:
    existing = set(package["projections"])
    if proposal not in existing:
        return proposal
    stem = proposal.removesuffix(".default.v1")
    index = 2
    while f"{stem}_{index}.default.v1" in existing:
        index += 1
    return f"{stem}_{index}.default.v1"


def _unique(proposal: str, existing: set[str]) -> str:
    if proposal not in existing:
        return proposal
    index = 2
    while f"{proposal}_{index}" in existing:
        index += 1
    return f"{proposal}_{index}"
