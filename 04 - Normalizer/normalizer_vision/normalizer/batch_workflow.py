"""Workflow stage for batch normalization orchestration."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.config import NormalizerExecutionConfig
from ..models.results import NormalizationResult
from ..prompts import PromptBundle
from ..release_runtime import ReleaseRuntime
from ..taxonomy import TaxonomyProfile
from .batch_limits import (
    build_batch_output_path as _build_batch_output_path,
    collect_batch_files as _collect_batch_files,
    emit_progress as _emit_progress,
    mark_batch_aborted_if_systemic as _mark_batch_aborted_if_systemic,
    resolve_worker_count as _resolve_worker_count,
)
from .batch_parallel import collect_parallel_results as _collect_parallel_results
from .types import ModelClient


def normalize_batch(
    *,
    project_root: Path,
    structured_dir: Path,
    output_root: Path,
    workers: int | None,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    provider_is_injected: bool,
    thread_pool_factory: Callable[..., Any],
    progress_callback: Callable[[NormalizationResult], None] | None,
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None = None,
) -> list[NormalizationResult]:
    worker_count = _resolve_worker_count(workers, config.default_workers, config.max_batch_workers)
    files = _collect_batch_files(structured_dir, config.max_batch_files)
    if provider_is_injected and worker_count > 1:
        worker_count = 1
    if worker_count == 1:
        return _normalize_batch_sequential(
            project_root=project_root,
            files=files,
            output_root=output_root,
            structured_dir=structured_dir,
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            progress_callback=progress_callback,
            sleep=sleep,
            release_runtime=release_runtime,
        )

    with thread_pool_factory(max_workers=worker_count) as pool:
        results = _collect_parallel_results(
            pool,
            iter(files),
            files=files,
            worker_count=worker_count,
            project_root=project_root,
            structured_dir=structured_dir,
            output_root=output_root,
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            progress_callback=progress_callback,
            sleep=sleep,
            release_runtime=release_runtime,
        )
    return results

def _normalize_batch_sequential(
    *,
    project_root: Path,
    files: list[Path],
    output_root: Path,
    structured_dir: Path,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    progress_callback: Callable[[NormalizationResult], None] | None,
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None = None,
) -> list[NormalizationResult]:
    from .workflow import normalize_document

    results: list[NormalizationResult] = []
    for file_path in files:
        result = normalize_document(
            project_root=project_root,
            structured_path=file_path,
            normalized_output_path=_build_batch_output_path(file_path, structured_dir=structured_dir, output_root=output_root),
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            sleep=sleep,
            release_runtime=release_runtime,
        )
        results.append(result)
        _emit_progress([result], progress_callback)
        if _mark_batch_aborted_if_systemic(result, remaining=len(files) - len(results)):
            break
    return results
