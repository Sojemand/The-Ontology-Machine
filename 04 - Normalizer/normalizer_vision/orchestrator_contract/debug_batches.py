"""Single and batch execution helpers for debug runs."""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from ..document_io import budget_normalized_output_file_name
from ..models.results import NormalizationResult
from ..normalizer import DocumentNormalizer
from ..normalizer.batch_workflow import _build_batch_output_path, _collect_batch_files, _resolve_worker_count
from . import debug_support
from .debug_results import log_result


def run_single(command, *, session_root: Path, output_root: Path, normalizer: DocumentNormalizer) -> tuple[list[NormalizationResult], int, bool]:
    source_path = command.source_path
    if source_path is None:
        raise ValueError("source_path fehlt oder ist ungueltig.")
    debug_support.write_snapshot(session_root, status="running", detail=source_path.name, processed=0, total=1)
    parent = output_root / "normalized"
    result = normalizer.normalize(source_path, parent / budget_normalized_output_file_name(parent, source_path))
    log_result(session_root, result)
    return [result], 1, debug_support.cancel_requested(session_root)


def run_batch(command, *, session_root: Path, output_root: Path, normalizer: DocumentNormalizer) -> tuple[list[NormalizationResult], int, bool]:
    input_root = command.input_root
    if input_root is None:
        raise ValueError("input_root fehlt oder ist ungueltig.")
    files = _collect_batch_files(input_root, normalizer.config.max_batch_files)
    worker_count = _resolve_worker_count(command.worker_count, normalizer.config.default_workers, normalizer.config.max_batch_workers)
    if not files:
        debug_support.write_snapshot(session_root, status="running", detail="Keine Structured-Dateien gefunden", total=0)
        return [], 0, debug_support.cancel_requested(session_root)
    debug_support.write_snapshot(session_root, status="running", detail=files[0].name, total=len(files))
    if worker_count == 1:
        return _run_batch_sequential(files, input_root=input_root, output_root=output_root, session_root=session_root, normalizer=normalizer)
    return _run_batch_parallel(
        files,
        input_root=input_root,
        output_root=output_root,
        session_root=session_root,
        normalizer=normalizer,
        worker_count=worker_count,
    )


def _run_batch_sequential(
    files: list[Path],
    *,
    input_root: Path,
    output_root: Path,
    session_root: Path,
    normalizer: DocumentNormalizer,
) -> tuple[list[NormalizationResult], int, bool]:
    results: list[NormalizationResult] = []
    total = len(files)
    for file_path in files:
        if debug_support.cancel_requested(session_root):
            return results, total, True
        debug_support.write_snapshot(
            session_root,
            status="running",
            detail=file_path.name,
            processed=len(results),
            total=total,
            counters=debug_support.counters_from_results(results),
        )
        result = normalizer.normalize(file_path, _build_batch_output_path(file_path, structured_dir=input_root, output_root=output_root))
        results.append(result)
        log_result(session_root, result)
    return results, total, debug_support.cancel_requested(session_root)


def _run_batch_parallel(
    files: list[Path],
    *,
    input_root: Path,
    output_root: Path,
    session_root: Path,
    normalizer: DocumentNormalizer,
    worker_count: int,
) -> tuple[list[NormalizationResult], int, bool]:
    results: list[NormalizationResult] = []
    pending = iter(files)
    futures: dict[object, Path] = {}
    cancelled = False
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        while len(futures) < min(worker_count, len(files)):
            _submit_next(pool, pending, futures, normalizer=normalizer, input_root=input_root, output_root=output_root)
        while futures:
            done, _ = wait(tuple(futures), return_when=FIRST_COMPLETED)
            _collect_done(done, futures, results, session_root=session_root, total=len(files))
            if debug_support.cancel_requested(session_root):
                cancelled = True
                continue
            while len(futures) < worker_count and _submit_next(pool, pending, futures, normalizer=normalizer, input_root=input_root, output_root=output_root):
                continue
    return sorted(results, key=lambda item: item.input_path), len(files), cancelled or debug_support.cancel_requested(session_root)


def _submit_next(pool, pending, futures: dict[object, Path], *, normalizer: DocumentNormalizer, input_root: Path, output_root: Path) -> bool:
    try:
        file_path = next(pending)
    except StopIteration:
        return False
    futures[pool.submit(normalizer.normalize, file_path, _build_batch_output_path(file_path, structured_dir=input_root, output_root=output_root))] = file_path
    return True


def _collect_done(done, futures: dict[object, Path], results: list[NormalizationResult], *, session_root: Path, total: int) -> None:
    for future in done:
        futures.pop(future)
        result = future.result()
        results.append(result)
        log_result(session_root, result)
        debug_support.write_snapshot(
            session_root,
            status="running",
            detail=Path(result.input_path).name,
            processed=len(results),
            total=total,
            counters=debug_support.counters_from_results(results),
        )
