"""Request artifact publication for successful pipeline records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import path_budget, policy, request_enrichment, storage_repository, success_publication
from .success_artifact_sources import artifact_sources

_MIN_MULTI_PAGE_REQUEST_DIR_LENGTH = len("a.12345678.p000.of000")
_MULTI_PAGE_REQUEST_RESERVED = _MIN_MULTI_PAGE_REQUEST_DIR_LENGTH + max(
    len(policy.request_file_name("ocr_request")),
    len(policy.request_file_name("interpreter_request")),
    len(policy.request_file_name("normalizer_request")),
) + 2


@dataclass(frozen=True)
class PublishedRequestArtifacts:
    optimizer_ocr_paths: list[Path]
    interpreter_paths: list[Path]
    normalizer_paths: list[Path]

    @property
    def all_paths(self) -> list[Path]:
        return [*self.optimizer_ocr_paths, *self.interpreter_paths, *self.normalizer_paths]


def publish_request_paths(
    engine: Any,
    record: Any,
    route_root: Path,
    allowed_roots: tuple[Path, ...],
    published_targets: list[Path],
    published_page_paths: list[Path],
    page_target_map: dict[Path, Path],
) -> PublishedRequestArtifacts | str:
    ocr_paths = _publish_plain_request_paths(
        engine,
        record,
        route_root,
        allowed_roots,
        published_targets,
        attr_list="optimizer_ocr_request_paths",
        attr_single="optimizer_ocr_request_path",
        request_key="ocr_request",
        purpose="OCR-Request",
        action="OCR request publication",
        noun="OCR request",
    )
    if isinstance(ocr_paths, str):
        return ocr_paths
    interpreter_paths = _publish_interpreter_request_paths(
        engine,
        record,
        route_root,
        allowed_roots,
        published_targets,
        published_page_paths,
        page_target_map,
    )
    if isinstance(interpreter_paths, str):
        return interpreter_paths
    normalizer_paths = _publish_plain_request_paths(
        engine,
        record,
        route_root,
        allowed_roots,
        published_targets,
        attr_list="normalizer_request_paths",
        attr_single="normalizer_request_path",
        request_key="normalizer_request",
        purpose="Normalizer-Request",
        action="Normalizer request publication",
        noun="Normalizer request",
    )
    if isinstance(normalizer_paths, str):
        return normalizer_paths
    return PublishedRequestArtifacts(ocr_paths, interpreter_paths, normalizer_paths)


def _publish_interpreter_request_paths(
    engine: Any,
    record: Any,
    route_root: Path,
    allowed_roots: tuple[Path, ...],
    published_targets: list[Path],
    published_page_paths: list[Path],
    page_target_map: dict[Path, Path],
) -> list[Path] | str:
    sources = artifact_sources(record, "interpreter_request_paths", "interpreter_request_path")
    published: list[Path] = []
    single_request = len(sources) == 1
    for source_path in sources:
        target = _request_target(engine, record, route_root, source_path, single_request, "interpreter_request")
        error = request_enrichment.publish_request_copy(
            engine,
            source_path,
            target,
            allowed_roots=allowed_roots,
            action="Request publication",
            noun="Interpreter request",
            source_target=success_publication.published_original_target(engine, record, route_root),
            page_targets=tuple(published_page_paths),
            page_target_map=page_target_map,
        )
        if error:
            success_publication.cleanup_published_targets(engine, published_targets, allowed_roots)
            return error
        published.append(target)
        published_targets.append(target)
    return published


def _publish_plain_request_paths(
    engine: Any,
    record: Any,
    route_root: Path,
    allowed_roots: tuple[Path, ...],
    published_targets: list[Path],
    *,
    attr_list: str,
    attr_single: str,
    request_key: str,
    purpose: str,
    action: str,
    noun: str,
    ) -> list[Path] | str:
    sources = artifact_sources(record, attr_list, attr_single)
    published: list[Path] = []
    single_request = len(sources) == 1
    for source_path in sources:
        target = _request_target(engine, record, route_root, source_path, single_request, request_key, purpose)
        error = success_publication.publish_file(
            engine,
            source_path,
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


def _request_target(
    engine: Any,
    record: Any,
    route_root: Path,
    source_path: Path,
    single_request: bool,
    request_key: str,
    purpose: str = "Interpreter-Request",
) -> Path:
    request_name = policy.request_file_name(request_key)
    publication_root = storage_repository.publication_root(route_root, "requests")
    request_root = publication_root / path_budget.budgeted_relative_path(
        publication_root,
        policy.record_relative_output_path(engine, record, purpose=purpose),
        reserved=_MULTI_PAGE_REQUEST_RESERVED if not single_request else 0,
    )
    if single_request:
        return request_root / request_name
    request_dir = request_root / path_budget.budgeted_page_name(
        request_root,
        source_path.parent.name,
        reserved=len(request_name) + 1,
    )
    target_name = request_name if request_key == "interpreter_request" else source_path.name
    return request_dir / path_budget.budgeted_name(request_dir, target_name)
