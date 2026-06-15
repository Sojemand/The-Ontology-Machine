"""Helper steps for publishing finalized success artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import path_budget, policy, storage_repository, success_publication
from .success_artifact_sources import artifact_sources, extra_request_page_images


@dataclass(frozen=True)
class PublishedPageAssets:
    primary_paths: list[Path]
    asset_target_map: dict[Path, Path]
    extra_working_paths: list[Path]


def publish_raw_paths(
    engine: Any,
    record: Any,
    route_root: Path,
    allowed_roots: tuple[Path, ...],
    published_targets: list[Path],
) -> list[Path] | str:
    published: list[Path] = []
    page_scoped = len(record.artifacts.optimizer_raw_paths) > 1
    for index, raw_path_text in enumerate(record.artifacts.optimizer_raw_paths):
        source = success_publication.existing_path(raw_path_text)
        if page_scoped:
            target_dir = storage_repository.publication_root(route_root, "raw_extracts") / policy.record_relative_output_path(engine, record, purpose="Raw-Output").parent
            target = target_dir / path_budget.budgeted_stage_name(target_dir, source.name)
        else:
            relative_target = success_publication.raw_target_path(engine, record, source, index=index)
            target_dir = storage_repository.publication_root(route_root, "raw_extracts") / relative_target.parent
            target = target_dir / path_budget.budgeted_stage_name(target_dir, relative_target.name)
        error = success_publication.publish_file(
            engine,
            source,
            target,
            allowed_roots=allowed_roots,
            action="Raw publication",
            noun="Optimizer raw output",
        )
        if error:
            success_publication.cleanup_published_targets(engine, published_targets, allowed_roots)
            return error
        published.append(target)
        published_targets.append(target)
    return published


def publish_page_images(
    engine: Any,
    record: Any,
    route_root: Path,
    allowed_roots: tuple[Path, ...],
    published_targets: list[Path],
) -> PublishedPageAssets | str:
    published: list[Path] = []
    target_map: dict[Path, Path] = {}
    sources = artifact_sources(record, "optimizer_page_image_paths", "")
    if not sources:
        return PublishedPageAssets(
            primary_paths=[],
            asset_target_map={},
            extra_working_paths=extra_request_page_images(record),
        )
    publication_root = storage_repository.publication_root(route_root, "page_images")
    target_dir = publication_root / _page_images_relative_dir(engine, record, publication_root)
    for source in sources:
        target = target_dir / path_budget.budgeted_name(target_dir, source.name)
        error = success_publication.publish_file(
            engine,
            source,
            target,
            allowed_roots=allowed_roots,
            action="Page image publication",
            noun="Optimizer page image",
        )
        if error:
            success_publication.cleanup_published_targets(engine, published_targets, allowed_roots)
            return error
        published.append(target)
        target_map[source] = target
        published_targets.append(target)
    return PublishedPageAssets(
        primary_paths=published,
        asset_target_map=target_map,
        extra_working_paths=extra_request_page_images(record),
    )


def publish_named_outputs(
    engine: Any,
    record: Any,
    route_root: Path,
    allowed_roots: tuple[Path, ...],
    published_targets: list[Path],
    *,
    attr_list: str,
    attr_single: str,
    publication_name: str,
    action: str,
    noun: str,
) -> list[Path] | str:
    published: list[Path] = []
    relative_parent = policy.record_relative_output_path(engine, record, purpose=noun).parent
    for source in artifact_sources(record, attr_list, attr_single):
        target_dir = storage_repository.publication_root(route_root, publication_name) / relative_parent
        target = target_dir / path_budget.budgeted_stage_name(target_dir, source.name)
        error = success_publication.publish_file(
            engine,
            source,
            target,
            allowed_roots=allowed_roots,
            action=action,
            noun=noun,
        )
        if error:
            success_publication.cleanup_published_targets(engine, published_targets, allowed_roots)
            return error
        published.append(target)
        published_targets.append(target)
    return published


def _page_images_relative_dir(engine: Any, record: Any, publication_root: Path) -> Path:
    relative_path = policy.record_relative_output_path(engine, record, purpose="Page image publication")
    image_dir_name = f"{relative_path.name}.{path_budget.hash8(record.content_hash)}"
    return path_budget.budgeted_relative_path(publication_root, relative_path.parent / image_dir_name, reserved=32)
