from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from normalizer_vision.taxonomy_sources import active_source_package_paths
from normalizer_vision.taxonomy_sources.governance import sync_release_governance


def package_paths(project_root: Path):
    return active_source_package_paths(project_root)


def read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root muss ein Objekt sein: {path}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def clone_locale(
    project_root: Path,
    *,
    source_locale: str = "en",
    target_locale: str,
    include_glossary: bool = False,
) -> None:
    paths = package_paths(project_root)
    release = read_yaml(paths.release_path)
    root = paths.root
    source_master_path = root / f"master.text.{source_locale}.yaml"
    target_master_path = root / f"master.text.{target_locale}.yaml"
    shutil.copyfile(source_master_path, target_master_path)
    for projection in paths.projections:
        shutil.copyfile(
            projection.text_path_for(source_locale),
            root / "projections" / f"{projection.projection_id}.text.{target_locale}.yaml",
        )
    glossary_locales = sorted(
        path.stem.removeprefix("translation_glossary.")
        for path in root.glob("translation_glossary.*.yaml")
    )
    if include_glossary:
        source_glossary_path = root / f"translation_glossary.{source_locale}.yaml"
        if source_glossary_path.exists():
            shutil.copyfile(
                source_glossary_path,
                root / f"translation_glossary.{target_locale}.yaml",
            )
            glossary_locales = sorted({*glossary_locales, target_locale})
    release["available_locales"] = sorted(
        {*(release.get("available_locales") or []), target_locale}
    )
    release.setdefault("default_authoring_locale", source_locale)
    release.setdefault("default_runtime_locale", source_locale)
    write_yaml(
        paths.release_path,
        sync_release_governance(release, glossary_locales=glossary_locales),
    )
