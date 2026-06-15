"""Helper functions for copying bundle artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import artifact_repository, page_image_assets, path_budget, policy, storage_repository


@dataclass(frozen=True)
class CopiedPageAssets:
    primary_paths: tuple[Path, ...]
    page_target_map: dict[Path, Path]


def copy_many(
    engine: Any,
    path_values: list[str],
    bundle_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    target_builder,
) -> list[Path]:
    copied: list[Path] = []
    for index, path_value in enumerate(path_values):
        source = Path(str(path_value).strip())
        if not source.exists():
            continue
        target = target_builder(source, index)
        artifact_repository.copy_if_exists(engine, source, target, allowed_roots=allowed_roots)
        if target.exists():
            copied.append(target)
    return copied


def copy_single(engine: Any, path_value: str, target: Path, *, allowed_roots: tuple[Path, ...]) -> Path | None:
    source = Path(str(path_value).strip())
    if not str(path_value).strip() or not source.exists():
        return None
    artifact_repository.copy_if_exists(engine, source, target, allowed_roots=allowed_roots)
    return target if target.exists() else None


def copy_named_many(
    engine: Any,
    path_values: list[str],
    target_root: Path,
    *,
    allowed_roots: tuple[Path, ...],
) -> list[Path]:
    copied: list[Path] = []
    for path_value in path_values:
        source = Path(str(path_value).strip())
        if not source.exists():
            continue
        target = target_root / path_budget.budgeted_stage_name(target_root, source.name)
        artifact_repository.copy_if_exists(engine, source, target, allowed_roots=allowed_roots)
        if target.exists():
            copied.append(target)
    return copied


def artifact_values(record: Any, list_attr: str, single_attr: str) -> list[str]:
    values = list(getattr(record.artifacts, list_attr, []) or [])
    if not values:
        single_value = str(getattr(record.artifacts, single_attr, "") or "").strip()
        values = [single_value] if single_value else []
    return values


def copy_page_images(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
) -> CopiedPageAssets:
    del engine, record, bundle_path, allowed_roots
    return CopiedPageAssets(primary_paths=(), page_target_map={})


def extra_request_page_images(record: Any) -> list[Path]:
    return page_image_assets.extra_render_paths_from_raws(
        record.artifacts.optimizer_raw_paths,
        known_path_values=record.artifacts.optimizer_page_image_paths,
    )


def raw_target_path(engine: Any, record: Any, source: Path, *, index: int) -> Path:
    if len(record.artifacts.optimizer_raw_paths) > 1:
        return policy.record_relative_output_path(engine, record, purpose="Raw-Output").parent / source.name
    if index == 0:
        return policy.raw_output_path(engine, record)
    return policy.raw_output_path(engine, record).with_name(source.name)


def budgeted_raw_target(
    engine: Any,
    record: Any,
    bundle_path: Path,
    source: Path,
    *,
    index: int,
    page_suffix: str,
) -> Path:
    raw_root = storage_repository.publication_root(bundle_path, "raw_extracts")
    relative_target = page_suffixed_path(raw_target_path(engine, record, source, index=index), page_suffix)
    target_dir = raw_root / relative_target.parent
    return target_dir / path_budget.budgeted_stage_name(target_dir, relative_target.name)


def page_suffixed_path(path: Path, page_suffix: str) -> Path:
    if not page_suffix:
        return path
    name = path.name
    for ending in (".raw.json", ".json"):
        if name.endswith(ending):
            return path.with_name(f"{name[:-len(ending)]}{page_suffix}{ending}")
    return path.with_name(f"{path.stem}{page_suffix}{path.suffix}")
