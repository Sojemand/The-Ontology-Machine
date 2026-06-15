"""Shared state helpers for page-scoped pipeline scheduling."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import threading
from typing import Any

from . import document_workflow
from .page_stage_types import PageWorkItem


class StageInbox:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._items: deque[Any] = deque()
        self._busy = False
        self._closed = False

    def send(self, item: Any, *, front: bool = False) -> bool:
        with self._condition:
            if self._closed:
                return False
            if front:
                self._items.appendleft(item)
            else:
                self._items.append(item)
            self._condition.notify_all()
            return True

    def receive(self) -> Any | None:
        with self._condition:
            while not self._items and not self._closed:
                self._condition.wait()
            if not self._items and self._closed:
                return None
            item = self._items.popleft()
            self._busy = True
            return item

    def complete(self) -> None:
        with self._condition:
            self._busy = False
            self._condition.notify_all()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()


@dataclass(slots=True)
class DocumentPageRun:
    active: document_workflow.ActiveRecordContext
    pages: list[PageWorkItem]
    page_image_paths: list[str] = field(default_factory=list)
    succeeded_pages: list[PageWorkItem] = field(default_factory=list)
    failed_pages: list[PageWorkItem] = field(default_factory=list)
    finalized: bool = False

    @property
    def terminal_count(self) -> int:
        return len(self.succeeded_pages) + len(self.failed_pages)
