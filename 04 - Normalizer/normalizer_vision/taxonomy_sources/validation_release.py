"""Release-level validation for source packages."""
from __future__ import annotations

from typing import Any

from . import governance, policy
from .types import SourcePackagePaths


def validate_release_payload(
    release: dict[str, Any],
    paths: SourcePackagePaths | None,
    *,
    projection_ids: list[str],
    glossary_locales: list[str],
) -> list[str]:
    policy.require_exact_keys(release, label="release", expected=("release_id", "release_version", "available_locales", "default_authoring_locale", "default_runtime_locale", "projection_ids", "governance"))
    release["release_id"] = policy.require_source_id(release.get("release_id"), label="release.release_id")
    policy.require_text(release.get("release_version"), label="release.release_version")
    available_locales = policy.canonical_locale_list(release.get("available_locales"), label="release.available_locales")
    if policy.require_locale_list(release.get("available_locales"), label="release.available_locales") != available_locales:
        raise ValueError("release.available_locales muss kanonisch sortiert sein.")
    default_authoring_locale = policy.require_locale(release.get("default_authoring_locale"), label="release.default_authoring_locale")
    default_runtime_locale = policy.require_locale(release.get("default_runtime_locale"), label="release.default_runtime_locale")
    if default_authoring_locale not in available_locales:
        raise ValueError("release.default_authoring_locale muss in release.available_locales enthalten sein.")
    if default_runtime_locale not in available_locales:
        raise ValueError("release.default_runtime_locale muss in release.available_locales enthalten sein.")
    canonical_projection_ids = _canonical_release_projection_ids(release, projection_ids)
    _validate_governance(release, paths, projection_ids=projection_ids, available_locales=available_locales, glossary_locales=glossary_locales)
    release["available_locales"] = available_locales
    release["default_authoring_locale"] = default_authoring_locale
    release["default_runtime_locale"] = default_runtime_locale
    release["projection_ids"] = canonical_projection_ids
    return available_locales


def _canonical_release_projection_ids(release: dict[str, Any], projection_ids: list[str]) -> list[str]:
    release_projection_ids = policy.require_projection_id_list(release.get("projection_ids"), label="release.projection_ids")
    canonical_projection_ids = policy.canonical_projection_id_list(release.get("projection_ids"), label="release.projection_ids")
    if release_projection_ids != canonical_projection_ids:
        raise ValueError("release.projection_ids muss kanonisch nach projection_id sortiert sein.")
    if release_projection_ids != projection_ids:
        raise ValueError("release.projection_ids passt nicht zur aktiven Release-Recipe.")
    return canonical_projection_ids


def _validate_governance(
    release: dict[str, Any],
    paths: SourcePackagePaths | None,
    *,
    projection_ids: list[str],
    available_locales: list[str],
    glossary_locales: list[str],
) -> None:
    governance_payload = policy.require_mapping(release.get("governance"), label="release.governance")
    policy.require_exact_keys(governance_payload, label="release.governance", expected=("source_package_blanket_exception",))
    exception = policy.require_mapping(governance_payload.get("source_package_blanket_exception"), label="release.governance.source_package_blanket_exception")
    policy.require_exact_keys(exception, label="release.governance.source_package_blanket_exception", expected=("kind", "allowed_file_count", "projection_count", "files"))
    expected_files = list(governance.expected_relative_files(projection_ids, available_locales, glossary_locales=glossary_locales))
    if policy.require_text(exception.get("kind"), label="release.governance.source_package_blanket_exception.kind") != governance.GOVERNANCE_KIND:
        raise ValueError(f"release.governance.source_package_blanket_exception.kind muss {governance.GOVERNANCE_KIND} sein.")
    if exception.get("allowed_file_count") != len(expected_files):
        raise ValueError("release.governance.source_package_blanket_exception.allowed_file_count ist ungueltig.")
    if exception.get("projection_count") != len(projection_ids):
        raise ValueError("release.governance.source_package_blanket_exception.projection_count ist ungueltig.")
    observed_files = policy.require_string_list(exception.get("files"), label="release.governance.source_package_blanket_exception.files")
    expected = list(paths.relative_files()) if paths is not None else expected_files
    if observed_files != expected:
        raise ValueError("release.governance.source_package_blanket_exception.files passt nicht zur Dateistruktur.")
