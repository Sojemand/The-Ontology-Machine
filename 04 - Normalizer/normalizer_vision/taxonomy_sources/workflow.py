"""Path resolution and loading workflow for taxonomy source packages."""
from __future__ import annotations

from pathlib import Path

from . import adapter
from . import policy as source_policy
from .types import LocaleSourcePaths, ProjectionSourcePaths, ProjectionTextSourcePath, SOURCE_ROOT_RELATIVE_PATH, SourcePackagePaths
from .validation import validate_source_package


def has_source_package(project_root: Path) -> bool:
    return bool(_discover_source_roots(project_root))


def active_source_package_paths(project_root: Path) -> SourcePackagePaths:
    candidates = _discover_source_roots(project_root)
    if not candidates:
        raise ValueError(f"Source-Paket fehlt: {project_root / SOURCE_ROOT_RELATIVE_PATH}")
    root = _select_source_root(project_root, candidates)
    return source_package_paths_for_root(root)


def source_package_paths_for_root(root: Path) -> SourcePackagePaths:
    release = adapter.load_yaml_mapping(root / "release.yaml", label="release")
    release_id = str(release.get("release_id") or "").strip()
    if root.name != release_id and root.name != "source_package":
        raise ValueError(f"Source-Paket-Ordner stimmt nicht mit release_id ueberein: {root}")
    projection_ids = source_policy.canonical_projection_id_list(
        release.get("projection_ids"),
        label="release.projection_ids",
    )
    available_locales = source_policy.canonical_locale_list(
        release.get("available_locales"),
        label="release.available_locales",
    )
    return _raw_source_package_paths(
        root,
        projection_ids=projection_ids,
        available_locales=available_locales,
    )


def load_source_package(project_root: Path) -> dict[str, object]:
    paths = active_source_package_paths(project_root)
    payload = validate_source_package(paths)
    return {"paths": paths, **payload}


def _discover_source_roots(project_root: Path) -> list[Path]:
    root = project_root / SOURCE_ROOT_RELATIVE_PATH
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "release.yaml").exists())


def _select_source_root(project_root: Path, candidates: list[Path]) -> Path:
    if len(candidates) == 1:
        return candidates[0]
    names = ", ".join(path.name for path in candidates)
    raise ValueError(f"Aktives Source-Paket ist mehrdeutig: {names}")


def _raw_source_package_paths(
    root: Path,
    *,
    projection_ids: list[str] | None = None,
    available_locales: list[str] | None = None,
) -> SourcePackagePaths:
    if projection_ids is None:
        release = adapter.load_yaml_mapping(root / "release.yaml", label="release")
        projection_ids = source_policy.canonical_projection_id_list(
            release.get("projection_ids"),
            label="release.projection_ids",
        )
        available_locales = source_policy.canonical_locale_list(
            release.get("available_locales"),
            label="release.available_locales",
        )
    if available_locales is None:
        release = adapter.load_yaml_mapping(root / "release.yaml", label="release")
        available_locales = source_policy.canonical_locale_list(
            release.get("available_locales"),
            label="release.available_locales",
        )
    locales = tuple(
        LocaleSourcePaths(
            locale=str(locale).strip(),
            master_text_path=root / f"master.text.{locale}.yaml",
            glossary_path=root / f"translation_glossary.{locale}.yaml",
            glossary_exists=(root / f"translation_glossary.{locale}.yaml").exists(),
        )
        for locale in available_locales
    )
    projections = tuple(
        ProjectionSourcePaths(
            projection_id=str(projection_id).strip(),
            core_path=root / "projections" / f"{projection_id}.core.yaml",
            texts=tuple(
                ProjectionTextSourcePath(
                    locale=str(locale).strip(),
                    text_path=root / "projections" / f"{projection_id}.text.{locale}.yaml",
                )
                for locale in available_locales
            ),
        )
        for projection_id in projection_ids
    )
    return SourcePackagePaths(
        root=root,
        release_path=root / "release.yaml",
        master_core_path=root / "master.core.yaml",
        locales=locales,
        projections=projections,
    )
