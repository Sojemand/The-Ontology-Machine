"""Workflow stage for source-backed profile listing, lookup, and loading."""
from __future__ import annotations

from pathlib import Path

from ..release_runtime import ReleaseRuntime
from ..runtime_semantic_assets.policy import build_projection_catalog as build_runtime_projection_catalog
from ..taxonomy import TaxonomyProfile, build_profile_from_master, build_profiles_from_compiled_master
from ..taxonomy_compile import compile_source_package, require_compiled_taxonomy_assets
from ..taxonomy_sources import policy as source_policy
from ..taxonomy_sources import active_source_package_paths, load_source_package
from .policy import sort_local_profiles
from .types import LocalProfileSpec, ProjectionCatalog
from .validation import require_profile_id


def list_local_profiles(project_root: Path) -> list[LocalProfileSpec]:
    compiled = require_compiled_taxonomy_assets(project_root)
    if compiled is None:
        return []
    source_paths = active_source_package_paths(project_root)
    core_paths = {
        projection.projection_id: projection.core_path
        for projection in source_paths.projections
    }
    return sort_local_profiles(
        [
            LocalProfileSpec(
                projection_id=projection_id,
                label=str(compiled.projections[projection_id].get("label") or "").strip(),
                source_path=core_paths[projection_id],
            )
            for projection_id in compiled.release["projection_ids"]
        ]
    )


def find_local_profile_spec(project_root: Path, profile_id: str) -> LocalProfileSpec | None:
    target = profile_id.strip()
    if not target:
        return None
    for spec in list_local_profiles(project_root):
        if spec.projection_id == target:
            return spec
    return None


def load_local_profile(project_root: Path, profile_id: str) -> TaxonomyProfile:
    target = require_profile_id(profile_id)
    compiled = _compiled_assets(project_root)
    payload = compiled.projections.get(target)
    if payload is None:
        raise ValueError(f"Lokales Taxonomie-Profil nicht gefunden: {target}")
    return build_profile_from_master(compiled.master, payload)


def load_local_profile_map(project_root: Path) -> dict[str, TaxonomyProfile]:
    compiled = _compiled_assets(project_root)
    return build_profiles_from_compiled_master(
        compiled.master,
        compiled.projections,
        list(compiled.release["projection_ids"]),
    )


def build_projection_catalog(project_root: Path) -> ProjectionCatalog:
    from ..semantic_release import build_semantic_release_core_from_compiled

    source_package, compiled, release_kwargs = _compiled_release_context(project_root)
    return build_runtime_projection_catalog(
        build_semantic_release_core_from_compiled(source_package, compiled, **release_kwargs)
    )


def build_local_release_runtime(project_root: Path, *, preferred_profile_id: str | None = None) -> ReleaseRuntime:
    from ..semantic_release import build_semantic_release_core_from_compiled

    source_package, compiled, release_kwargs = _compiled_release_context(project_root)
    profiles = build_profiles_from_compiled_master(
        compiled.master,
        compiled.projections,
        list(compiled.release["projection_ids"]),
    )
    if not profiles:
        raise ValueError("Source-Paket enthaelt keine nutzbaren Projection-Profile.")
    preferred = str(preferred_profile_id or "").strip()
    fallback_projection_id = preferred if preferred in profiles else str(compiled.release["projection_ids"][0])
    catalog = build_runtime_projection_catalog(
        build_semantic_release_core_from_compiled(source_package, compiled, **release_kwargs)
    )
    return ReleaseRuntime(
        profiles=profiles,
        fallback_profile=profiles[fallback_projection_id],
        catalog_version=catalog.catalog_version,
    )


def _compiled_release_context(project_root: Path):
    from ..semantic_release.recipe import load_recipe

    recipe = load_recipe(project_root)
    projection_ids = source_policy.canonical_projection_id_list(
        list(recipe["projection_ids"]),
        label="projection_ids",
    )
    source_package = load_source_package(project_root)
    compiled = compile_source_package(source_package, projection_ids=projection_ids)
    release_kwargs = {
        "release_id": str(recipe["release_id"]).strip() or "semantic_release.default",
        "release_version": str(recipe["release_version"]).strip() or "1",
        "materialization_version": str(recipe["materialization_version"]).strip() or "1",
    }
    return source_package, compiled, release_kwargs


def _compiled_assets(project_root: Path):
    package = load_source_package(project_root)
    return compile_source_package(package)
