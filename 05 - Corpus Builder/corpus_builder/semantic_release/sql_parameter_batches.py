from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")

SAFE_SQL_PARAMETER_BATCH_SIZE = 900


def iter_parameter_batches(
    values: Iterable[T],
    *,
    reserved_parameters: int = 0,
    batch_size: int = SAFE_SQL_PARAMETER_BATCH_SIZE,
) -> Iterator[tuple[T, ...]]:
    available = batch_size - reserved_parameters
    if available <= 0:
        raise ValueError("reserved_parameters must leave at least one SQL parameter slot.")
    batch: list[T] = []
    for value in values:
        batch.append(value)
        if len(batch) >= available:
            yield tuple(batch)
            batch.clear()
    if batch:
        yield tuple(batch)
