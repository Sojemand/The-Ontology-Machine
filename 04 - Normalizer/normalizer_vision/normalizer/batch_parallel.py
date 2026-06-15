"""Bounded parallel execution helpers for batch normalization."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import FIRST_COMPLETED, wait
from pathlib import Path
from typing import Any

from ..models.config import NormalizerExecutionConfig
from ..models.results import NormalizationResult
from ..prompts import PromptBundle
from ..release_runtime import ReleaseRuntime
from ..taxonomy import TaxonomyProfile
from .batch_limits import build_batch_output_path, emit_progress, mark_batch_aborted_if_systemic
from .types import ModelClient


def collect_parallel_results(
    pool,
    pending: Iterator[Path],
    *,
    files: list[Path],
    worker_count: int,
    project_root: Path,
    structured_dir: Path,
    output_root: Path,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    progress_callback: Callable[[NormalizationResult], None] | None,
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None,
) -> list[NormalizationResult]:
    futures: dict[Any, Path] = {}
    while len(futures) < min(worker_count, len(files)):
        if not _submit_next(
            pool,
            pending,
            futures,
            project_root=project_root,
            structured_dir=structured_dir,
            output_root=output_root,
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            sleep=sleep,
            release_runtime=release_runtime,
        ):
            break

    results: list[NormalizationResult] = []
    while futures:
        done, _ = wait(tuple(futures), return_when=FIRST_COMPLETED)
        for future in done:
            futures.pop(future)
            result = future.result()
            results.append(result)
            emit_progress([result], progress_callback)
            if mark_batch_aborted_if_systemic(result, remaining=len(files) - len(results) - len(futures)):
                for pending_future in futures:
                    pending_future.cancel()
                return sorted(results, key=lambda item: item.input_path)
        while len(futures) < worker_count and _submit_next(
            pool,
            pending,
            futures,
            project_root=project_root,
            structured_dir=structured_dir,
            output_root=output_root,
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            sleep=sleep,
            release_runtime=release_runtime,
        ):
            continue
    return sorted(results, key=lambda item: item.input_path)


def _submit_next(
    pool,
    pending: Iterator[Path],
    futures: dict[Any, Path],
    *,
    project_root: Path,
    structured_dir: Path,
    output_root: Path,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None,
) -> bool:
    from .workflow import normalize_document

    try:
        file_path = next(pending)
    except StopIteration:
        return False
    futures[
        pool.submit(
            normalize_document,
            project_root=project_root,
            structured_path=file_path,
            normalized_output_path=build_batch_output_path(file_path, structured_dir=structured_dir, output_root=output_root),
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            sleep=sleep,
            release_runtime=release_runtime,
        )
    ] = file_path
    return True
