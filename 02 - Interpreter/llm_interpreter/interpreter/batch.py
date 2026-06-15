"""Batch execution helpers for the interpreter workflow stage."""
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from ..providers import ProviderError
from . import adapter


def validate_num_workers(num_workers: int, max_workers: int) -> None:
    if num_workers <= 0:
        raise ProviderError("num_workers muss positiv sein")
    if num_workers > max_workers:
        raise ProviderError(f"num_workers ueberschreitet das Limit von {max_workers}")


def run_sequential_batch(planned, results, total, config, on_progress, create_provider_fn, process_single_fn, should_cancel: Callable[[], bool] | None = None) -> None:
    try:
        provider = create_provider_fn(config.model, timeout=config.timeout_seconds, base_url=config.api_base_url)
        provider_error = None
    except Exception as exc:
        provider = None
        provider_error = str(exc)
    for done, item in enumerate(planned, start=1):
        if _cancel_requested(should_cancel):
            result = _cancelled_result(item)
        elif item.collision_error:
            result = adapter.build_batch_error_result(item.file_path, item.output_path, item.collision_error)
        elif provider is None:
            result = adapter.build_batch_error_result(item.file_path, None, provider_error or "Provider nicht verfuegbar")
        else:
            result = process_single_fn(item.file_path, item.output_path, config, provider)
        results[item.index] = result
        if on_progress:
            on_progress(result, done, total)


def run_parallel_batch(planned, results, total, config, on_progress, create_provider_fn, process_single_fn, num_workers, should_cancel: Callable[[], bool] | None = None) -> None:
    done = 0
    work_items = []

    def _record(item, result) -> None:
        nonlocal done
        results[item.index] = result
        done += 1
        if on_progress:
            on_progress(result, done, total)

    for item in planned:
        if _cancel_requested(should_cancel):
            _record(item, _cancelled_result(item))
        elif item.collision_error:
            result = adapter.build_batch_error_result(item.file_path, item.output_path, item.collision_error)
            _record(item, result)
        else:
            work_items.append(item)

    def _worker(item):
        provider = create_provider_fn(config.model, timeout=config.timeout_seconds, base_url=config.api_base_url)
        return process_single_fn(item.file_path, item.output_path, config, provider)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        next_index = 0
        stop_submitting = False

        def _submit_next() -> bool:
            nonlocal next_index, stop_submitting
            if stop_submitting or next_index >= len(work_items):
                return False
            if _cancel_requested(should_cancel):
                stop_submitting = True
                return False
            item = work_items[next_index]
            next_index += 1
            futures[executor.submit(_worker, item)] = item
            return True

        while len(futures) < num_workers and _submit_next():
            pass
        while futures:
            completed, _pending = wait(futures, return_when=FIRST_COMPLETED)
            for future in completed:
                item = futures.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = adapter.build_batch_error_result(item.file_path, item.output_path, str(exc))
                _record(item, result)
            while len(futures) < num_workers and _submit_next():
                pass
    while next_index < len(work_items):
        item = work_items[next_index]
        next_index += 1
        _record(item, _cancelled_result(item))


def _cancel_requested(should_cancel: Callable[[], bool] | None) -> bool:
    return bool(should_cancel is not None and should_cancel())


def _cancelled_result(item) -> dict:
    result = adapter.build_batch_error_result(item.file_path, item.output_path, "Batch abgebrochen")
    result["status"] = "cancelled"
    return result


__all__ = ["run_parallel_batch", "run_sequential_batch", "validate_num_workers"]
