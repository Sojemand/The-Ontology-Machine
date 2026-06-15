"""Shared helpers for source-layer review actions."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from ..models import load_config
from ..projection_routing.arbitration import select_advisory_projection
from ..projection_routing.config import load_routing_settings
from ..projection_routing.policy import extract_projection_hint, score_profile
from ..projection_routing.types import ProjectionSelection
from ..semantic_release.policy import analyze_taxonomy_shape, build_release_fingerprint
from ..taxonomy import TaxonomyProfile, build_profile_from_master
from ..taxonomy_compile import compile_source_package
from . import adapter

_PHRASE_SPLIT_RE = re.compile(r"[\n,;]+")
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._/-]*", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "is",
        "are",
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "into",
    }
)
_SECTION_HINTS = {
    "document_types": ("rechnung", "mahnung", "angebot", "vertrag", "bescheid", "notice", "invoice"),
    "field_codes": ("betrag", "datum", "nummer", "konto", "adresse", "amount", "date", "address"),
    "row_types": ("position", "zeile", "historie", "history", "verlauf"),
    "cell_codes": ("saldo", "steuer", "summe", "anteil", "share", "total"),
}


def load_review_context(project_root: Path) -> dict[str, Any]:
    context = adapter.load_context(project_root)
    compiled = compile_source_package(context["package"])
    profiles = {
        projection_id: build_profile_from_master(compiled.master, compiled.projections[projection_id])
        for projection_id in compiled.release["projection_ids"]
    }
    config = load_config(project_root)
    return {
        "package": context["package"],
        "compiled": compiled,
        "profiles": profiles,
        "config": config,
        "routing_settings": load_routing_settings(project_root),
        "release_preview": _release_preview(compiled, context["materialization_version"]),
    }


def select_review_projection(context: dict[str, Any], raw_doc: dict[str, Any]) -> tuple[ProjectionSelection, list[dict[str, Any]]]:
    profiles: dict[str, TaxonomyProfile] = context["profiles"]
    config = context["config"]
    fallback = profiles.get(config.taxonomy_profile_id) or profiles[next(iter(profiles))]
    ranking = []
    for projection_id, profile in profiles.items():
        score, signals = score_profile(profile, raw_doc, context["routing_settings"])
        ranking.append({"projection_id": projection_id, "score": score, "signals": signals, "profile": profile})
    ranking.sort(key=lambda item: (-int(item["score"]), str(item["projection_id"])))
    selection = _selection_from_ranking(ranking, raw_doc, fallback, config.projection_hint_mode, context["routing_settings"])
    return selection, ranking


def split_statements(*texts: str) -> list[str]:
    statements: list[str] = []
    for text in texts:
        for item in _PHRASE_SPLIT_RE.split(str(text or "")):
            normalized = " ".join(item.split()).strip()
            if normalized:
                statements.append(normalized)
    return statements


def keyword_phrases(*texts: str) -> list[str]:
    phrases = split_statements(*texts)
    for text in texts:
        normalized = normalize_text(text)
        for token in _TOKEN_RE.finditer(normalized):
            word = token.group(0).casefold()
            if len(word) > 2 and word not in _STOPWORDS:
                phrases.append(word)
    return _dedupe(phrases)


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(text.split())


def compact_ranking(ranking: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    return [
        {"projection_id": str(item["projection_id"]), "score": int(item["score"]), "signals": list(item["signals"])[:6]}
        for item in ranking[:limit]
    ]


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        tokens: list[str] = []
        for key, child in value.items():
            tokens.append(str(key))
            tokens.extend(flatten_strings(child))
        return tokens
    if isinstance(value, list):
        tokens: list[str] = []
        for child in value:
            tokens.extend(flatten_strings(child))
        return tokens
    if value in (None, ""):
        return []
    return [str(value)]


def excerpt_text(value: Any, *, limit: int = 160) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def infer_section_id(text: str) -> str:
    normalized = normalize_text(text)
    for section_id, markers in _SECTION_HINTS.items():
        if any(marker in normalized for marker in markers):
            return section_id
    return "categories"


def _selection_from_ranking(ranking, raw_doc, fallback, hint_mode: str, routing_settings) -> ProjectionSelection:
    profiles = {item["projection_id"]: item["profile"] for item in ranking}
    hint = extract_projection_hint(raw_doc)
    if hint_mode == "off":
        return ProjectionSelection(fallback, "hint_disabled", hint.projection_id, hint.confidence, None, "projection_hint_mode=off; using configured fallback profile.")
    if hint_mode == "strict":
        if hint.projection_id and hint.projection_id in profiles:
            return ProjectionSelection(profiles[hint.projection_id], "hint_strict", hint.projection_id, hint.confidence, None, "projection_hint_mode=strict; using valid interpreter hint directly.")
        return ProjectionSelection(fallback, "hint_strict_fallback", hint.projection_id, hint.confidence, None, "projection_hint_mode=strict, but no valid hint is present; using fallback profile.")
    if hint.projection_id:
        scores = {item["projection_id"]: (int(item["score"]), list(item["signals"])) for item in ranking}
        decision = select_advisory_projection(scores=scores, fallback_projection_id=fallback.projection_id, hint=hint, routing_settings=routing_settings)
        return ProjectionSelection(profiles.get(decision.projection_id, fallback), decision.mode, hint.projection_id, hint.confidence, None, decision.reason)
    return ProjectionSelection(fallback, "fallback", None, None, None, "No projection_hint in input; using configured fallback profile.")


def _release_preview(compiled, materialization_version: str) -> dict[str, Any]:
    projections = [compiled.projections[projection_id] for projection_id in compiled.release["projection_ids"]]
    payload = {
        "release_id": compiled.release["release_id"],
        "release_version": compiled.release["release_version"],
        "projection_ids": list(compiled.release["projection_ids"]),
        "materialization_version": materialization_version,
        "master_taxonomy_id": compiled.master["taxonomy_id"],
        "master_taxonomy_version": compiled.master["taxonomy_version"],
        "analysis": analyze_taxonomy_shape(compiled.master, projections),
        "fingerprint": "",
    }
    payload["fingerprint"] = build_release_fingerprint(payload)
    return payload


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(str(value).strip())
    return result
