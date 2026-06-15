"""Derived governance helpers for release-local source packages."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import policy

GOVERNANCE_KIND = "locale_aware_source_package"


def expected_relative_files(
    projection_ids: list[str],
    available_locales: list[str],
    *,
    glossary_locales: list[str] | tuple[str, ...] = (),
) -> tuple[str, ...]:
    projection_ids = policy.canonical_projection_id_list(
        projection_ids,
        label="projection_ids",
    )
    locales = sorted(str(locale).strip().casefold() for locale in available_locales if str(locale).strip())
    glossary_locale_set = {
        str(locale).strip().casefold()
        for locale in glossary_locales
        if str(locale).strip()
    }
    files = [
        "release.yaml",
        "master.core.yaml",
    ]
    for locale in locales:
        files.append(f"master.text.{locale}.yaml")
    for locale in locales:
        if locale in glossary_locale_set:
            files.append(f"translation_glossary.{locale}.yaml")
    for projection_id in projection_ids:
        files.append(f"projections/{projection_id}.core.yaml")
        for locale in locales:
            files.append(f"projections/{projection_id}.text.{locale}.yaml")
    return tuple(files)


def sync_release_governance(
    release: dict[str, Any],
    *,
    glossary_locales: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    payload = deepcopy(release)
    projection_ids = policy.canonical_projection_id_list(
        payload.get("projection_ids"),
        label="release.projection_ids",
    )
    available_locales = policy.canonical_locale_list(
        payload.get("available_locales"),
        label="release.available_locales",
    )
    payload["projection_ids"] = projection_ids
    payload["available_locales"] = available_locales
    payload["default_authoring_locale"] = policy.require_locale(
        payload.get("default_authoring_locale"),
        label="release.default_authoring_locale",
    )
    payload["default_runtime_locale"] = policy.require_locale(
        payload.get("default_runtime_locale"),
        label="release.default_runtime_locale",
    )
    normalized_glossaries = {
        str(locale).strip().casefold()
        for locale in glossary_locales
        if str(locale).strip()
    }
    files = list(
        expected_relative_files(
            projection_ids,
            available_locales,
            glossary_locales=[
                locale for locale in available_locales if locale in normalized_glossaries
            ],
        )
    )
    payload["governance"] = {
        "source_package_blanket_exception": {
            "kind": GOVERNANCE_KIND,
            "allowed_file_count": len(files),
            "projection_count": len(projection_ids),
            "files": files,
        }
    }
    return payload
