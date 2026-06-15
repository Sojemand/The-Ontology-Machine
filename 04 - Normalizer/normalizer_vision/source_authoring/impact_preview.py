"""Reusable candidate-impact preview for source authoring workflows."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.serialization import utc_now_iso
from ..semantic_release.policy import analyze_taxonomy_shape, build_release_fingerprint
from ..taxonomy import SEMANTIC_RELEASE_SCHEMA_VERSION
from ..taxonomy_compile import compile_source_package
from ..taxonomy_sources import load_source_package


def describe_package_delta(project_root: Path, package: dict[str, Any], *, materialization_version: str) -> dict[str, object]:
    current_package = load_source_package(project_root)
    current_compiled = compile_source_package(current_package)
    candidate_compiled = compile_source_package(package)
    current_release = _release_payload(
        current_compiled.master,
        current_compiled.projections,
        current_compiled.release,
        materialization_version,
    )
    candidate_release = _release_payload(
        candidate_compiled.master,
        candidate_compiled.projections,
        candidate_compiled.release,
        materialization_version,
    )
    changed_source_files = _changed_source_files(current_package, package)
    return {
        "compiled": candidate_compiled,
        "changed_source_files": changed_source_files,
        "current_release_fingerprint": str(current_release["fingerprint"]),
        "candidate_release_fingerprint": str(candidate_release["fingerprint"]),
        "release_fingerprint_changed": str(current_release["fingerprint"]) != str(candidate_release["fingerprint"]),
    }


def _release_payload(
    master: dict[str, Any],
    projections: dict[str, dict[str, Any]],
    release_meta: dict[str, Any],
    materialization_version: str,
) -> dict[str, Any]:
    ordered = [projections[projection_id] for projection_id in release_meta["projection_ids"]]
    release = {
        "schema_version": SEMANTIC_RELEASE_SCHEMA_VERSION,
        "release_id": release_meta["release_id"],
        "release_version": release_meta["release_version"],
        "master_taxonomy_id": master.get("taxonomy_id"),
        "master_taxonomy_version": master.get("taxonomy_version"),
        "projection_ids": list(release_meta["projection_ids"]),
        "materialization_version": materialization_version,
        "created_at": utc_now_iso(),
        "fingerprint": "",
        "master_taxonomy": master,
        "projections": ordered,
        "analysis": analyze_taxonomy_shape(master, ordered),
    }
    release["fingerprint"] = build_release_fingerprint(release)
    return release


def _changed_source_files(current_package: dict[str, Any], candidate_package: dict[str, Any]) -> list[str]:
    current_files = _package_files(current_package)
    candidate_files = _package_files(candidate_package)
    return [
        path
        for path in sorted(set(current_files) | set(candidate_files))
        if _canonical(current_files.get(path)) != _canonical(candidate_files.get(path))
    ]


def _package_files(package: dict[str, Any]) -> dict[str, Any]:
    files: dict[str, Any] = {
        "release.yaml": package["release"],
        "master.core.yaml": package["master"]["core"],
    }
    available_locales = list(package["release"]["available_locales"])
    for locale in available_locales:
        files[f"master.text.{locale}.yaml"] = package["master"]["texts"][locale]
        glossary = package.get("glossaries", {}).get(locale)
        if glossary and glossary.get("glossary"):
            files[f"translation_glossary.{locale}.yaml"] = glossary
    for projection_id in package["release"]["projection_ids"]:
        projection = package["projections"][projection_id]
        files[f"projections/{projection_id}.core.yaml"] = projection["core"]
        for locale in available_locales:
            files[f"projections/{projection_id}.text.{locale}.yaml"] = projection["texts"][locale]
    return files


def _canonical(payload: Any) -> str:
    return json.dumps(payload if payload is not None else {}, ensure_ascii=False, sort_keys=True)
