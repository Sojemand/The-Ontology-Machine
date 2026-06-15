"""Fail-closed validation for locale-aware taxonomy source packages."""
from __future__ import annotations

from typing import Any

from . import adapter, policy, semantic_validation
from .types import SourcePackagePaths
from .validation_release import validate_release_payload
from .validation_sections import (
    validate_glossary,
    validate_locale_mapping_keys,
    validate_master_core,
    validate_master_text,
    validate_projection_core,
    validate_projection_text,
)


def validate_source_package(paths: SourcePackagePaths) -> dict[str, object]:
    _validate_filesystem(paths)
    release = adapter.load_yaml_mapping(paths.release_path, label="release")
    master_core = adapter.load_yaml_mapping(paths.master_core_path, label="master.core")
    master_texts = {locale_paths.locale: adapter.load_yaml_mapping(locale_paths.master_text_path, label=f"master.text.{locale_paths.locale}") for locale_paths in paths.locales}
    glossaries = {locale_paths.locale: adapter.load_yaml_mapping(locale_paths.glossary_path, label=f"translation_glossary.{locale_paths.locale}") for locale_paths in paths.locales if locale_paths.glossary_exists}
    projections: dict[str, dict[str, Any]] = {}
    for projection in paths.projections:
        projections[projection.projection_id] = {
            "core": adapter.load_yaml_mapping(projection.core_path, label=f"{projection.projection_id}.core"),
            "texts": {item.locale: adapter.load_yaml_mapping(item.text_path, label=f"{projection.projection_id}.text.{item.locale}") for item in projection.texts},
        }
    payload = {"release": release, "master": {"core": master_core, "texts": master_texts}, "glossaries": glossaries, "projections": projections}
    return validate_source_package_payload(payload, paths=paths)


def validate_source_package_payload(payload: dict[str, object], *, paths: SourcePackagePaths | None = None) -> dict[str, object]:
    release = policy.require_mapping(payload.get("release"), label="release")
    master = policy.require_mapping(payload.get("master"), label="master")
    master_core = policy.require_mapping(master.get("core"), label="master.core")
    master_texts = policy.require_mapping(master.get("texts"), label="master.texts")
    glossaries = policy.optional_mapping(payload.get("glossaries"), label="glossaries")
    projections = policy.require_mapping(payload.get("projections"), label="projections")
    projection_ids = (
        policy.require_projection_id_list(release.get("projection_ids"), label="release.projection_ids")
        if paths is None
        else policy.canonical_projection_id_list([projection.projection_id for projection in paths.projections], label="source_package_paths.projection_ids")
    )
    available_locales = validate_release_payload(release, paths, projection_ids=projection_ids, glossary_locales=sorted(glossaries))
    projection_ids = list(release["projection_ids"])
    validate_master_core(master_core)
    validate_locale_mapping_keys(master_texts, label="master.texts", available_locales=available_locales, require_all=True)
    validate_locale_mapping_keys(glossaries, label="glossaries", available_locales=available_locales, require_all=False)
    for locale in available_locales:
        validate_master_text(policy.require_mapping(master_texts.get(locale), label=f"master.texts.{locale}"), locale=locale)
    for locale, glossary in glossaries.items():
        validate_glossary(policy.require_mapping(glossary, label=f"glossaries.{locale}"), locale=locale)
    _validate_projections(projections, projection_ids=projection_ids, available_locales=available_locales)
    validated = {"release": release, "master": {"core": master_core, "texts": master_texts}, "glossaries": glossaries, "projections": projections}
    semantic_validation.validate_source_package_semantics(validated)
    return validated


def _validate_projections(projections: dict[str, Any], *, projection_ids: list[str], available_locales: list[str]) -> None:
    for projection_id in projection_ids:
        parts = policy.require_mapping(projections.get(projection_id), label=f"projections.{projection_id}")
        core = policy.require_mapping(parts.get("core"), label=f"{projection_id}.core")
        text_payloads = policy.require_mapping(parts.get("texts"), label=f"{projection_id}.texts")
        validate_locale_mapping_keys(text_payloads, label=f"{projection_id}.texts", available_locales=available_locales, require_all=True)
        validate_projection_core(core, projection_id=projection_id)
        for locale in available_locales:
            validate_projection_text(policy.require_mapping(text_payloads.get(locale), label=f"{projection_id}.texts.{locale}"), locale=locale)


def _validate_filesystem(paths: SourcePackagePaths) -> None:
    if not paths.root.exists():
        raise ValueError(f"Source-Paket fehlt: {paths.root}")
    expected = set(paths.relative_files())
    observed = set(adapter.discover_relative_files(paths.root))
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        details = [f"fehlend: {', '.join(missing)}" for missing in [missing] if missing]
        details.extend(f"extra: {', '.join(extra)}" for extra in [extra] if extra)
        raise ValueError(f"Source-Paket-Dateiliste ist ungueltig ({'; '.join(details)})")
