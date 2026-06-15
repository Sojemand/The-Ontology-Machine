from __future__ import annotations

import queue

import pytest


def drain_events(worker_queue) -> list[str]:
    events: list[str] = []
    while True:
        try:
            events.append(worker_queue.get_nowait()[0])
        except queue.Empty:
            return events


class QueueStub:
    def __init__(self) -> None:
        self.items: list[tuple[str, object]] = []

    def put(self, item: tuple[str, object]) -> None:
        self.items.append(item)


class EventStub:
    def __init__(self, is_set: bool = False) -> None:
        self._is_set = is_set

    def is_set(self) -> bool:
        return self._is_set


def spawn_queue_or_skip(ctx):
    try:
        return ctx.Queue()
    except PermissionError as exc:
        pytest.skip(f"Spawn-Queue in dieser Umgebung nicht verfuegbar: {exc}")
