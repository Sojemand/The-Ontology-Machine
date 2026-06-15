"""Validate, compile, and export source packages."""
from __future__ import annotations

from typing import Any

from ..semantic_release import default_publish_output_path
from ..taxonomy_sources import policy as source_policy
from . import adapter
from .operation_common import (
    ensure_compiled,
    locale_source,
    optional_bundle_path,
    optional_locale,
    publish_release,
)
from .response import build_response


def validate_release_package(project_root, payload: dict[str, Any] | None = None) -> dict[str, object]:
    payload = payload or {}
    context = adapter.load_context(project_root)
    release = context["package"]["release"]
    target_locale = optional_locale(payload.get("target_locale"), label="target_locale")
    summary_lines = [
        f"Release: {release['release_id']}",
        f"Version: {release['release_version']}",
        f"Projections: {len(release['projection_ids'])}",
    ]
    extras: dict[str, object] = {}
    if target_locale is not None:
        source_policy.materialize_locale_view(context["package"], locale=target_locale)
        summary_lines.append(f"Target locale: {target_locale} (explicit_target_locale)")
        extras["locale_resolution"] = {"runtime_locale": target_locale, "source": "explicit_target_locale"}
    return build_response(
        "validate_release_package",
        headline="Release package validated",
        summary_lines=summary_lines,
        required_fields=[
            "release_id",
            "release_version",
            "available_locales",
            "default_authoring_locale",
            "default_runtime_locale",
            "projection_ids",
        ],
        references_existing_codes=release["projection_ids"],
        **extras,
    )


def compile_release_package(project_root, payload: dict[str, Any] | None = None) -> dict[str, object]:
    payload = payload or {}
    target_locale = optional_locale(payload.get("target_locale"), label="target_locale")
    compiled = ensure_compiled(project_root, target_locale=target_locale)
    if compiled is None:
        raise ValueError("Aktives Source-Paket fehlt.")
    runtime_locale = str(compiled.release.get("runtime_locale") or "").strip()
    source = locale_source(target_locale)
    return build_response(
        "compile_release_package",
        headline="Source package compiled",
        summary_lines=[f"Compiled projections: {len(compiled.release['projection_ids'])}", f"Runtime locale: {runtime_locale} ({source})"],
        references_existing_codes=compiled.release["projection_ids"],
        runtime_locale=runtime_locale,
        locale_resolution={"runtime_locale": runtime_locale, "source": source},
        compile_effect="Compile validates the saved source package and materializes release-ready taxonomy payloads in memory.",
    )


def export_semantic_release(project_root, payload: dict[str, Any]) -> dict[str, object]:
    target_locale = optional_locale(payload.get("target_locale"), label="target_locale")
    if target_locale is None:
        _validate_release_package(project_root)
    else:
        _validate_release_package(project_root, {"target_locale": target_locale})
    compiled = ensure_compiled(project_root, target_locale=target_locale)
    if compiled is None:
        raise ValueError("Aktives Source-Paket fehlt.")
    output_path = optional_bundle_path(payload.get("output_path"), label="output_path")
    release = publish_release(project_root, output_path, target_locale=target_locale)
    runtime_locale = str(release.get("runtime_locale") or "").strip()
    target_path = output_path or default_publish_output_path(
        project_root,
        release["release_id"],
        release_version=release["release_version"],
        runtime_locale=runtime_locale,
    )
    return build_response(
        "export_semantic_release",
        headline="Semantic release exported",
        summary_lines=[
            f"Release: {release['release_id']}",
            f"Version: {release['release_version']}",
            f"Runtime locale: {runtime_locale} ({locale_source(target_locale)})",
            f"Fingerprint: {release['fingerprint']}",
        ],
        required_fields=["output_path"],
        references_existing_codes=release["projection_ids"],
        output_path=str(target_path),
        runtime_locale=runtime_locale,
        locale_resolution={"runtime_locale": runtime_locale, "source": locale_source(target_locale)},
        artifacts=[{"label": "Release Bundle", "value": str(target_path)}],
        compile_effect="Source files were validated and compiled before the JSON release bundle was exported.",
        corpus_effect="The exported JSON release bundle can now be staged or activated by the Corpus Builder.",
    )


def _validate_release_package(project_root, payload: dict[str, Any] | None = None) -> dict[str, object]:
    from . import operations as operations_facade

    validator = getattr(operations_facade, "validate_release_package", validate_release_package)
    if payload is None:
        return validator(project_root)
    return validator(project_root, payload)
