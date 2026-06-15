from __future__ import annotations

from types import SimpleNamespace

from orchestrator.ui import queue_scheduler, responsive, save_scheduler, workflow


class _Card:
    def __init__(self) -> None:
        self.grid_calls = 0
        self.forget_calls = 0

    def grid(self, **_kwargs) -> None:
        self.grid_calls += 1

    def grid_forget(self) -> None:
        self.forget_calls += 1


class _Container:
    def __init__(self) -> None:
        self.columns: list[tuple[int, int]] = []

    def grid_columnconfigure(self, column: int, weight: int) -> None:
        self.columns.append((column, weight))


class _Label:
    def __init__(self) -> None:
        self.wraps: list[int] = []

    def configure(self, **kwargs) -> None:
        if "wraplength" in kwargs:
            self.wraps.append(int(kwargs["wraplength"]))


class _TimerApp:
    def __init__(self) -> None:
        self.jobs: dict[str, object] = {}
        self.counter = 0

    def after(self, _delay, callback):
        self.counter += 1
        handle = f"job-{self.counter}"
        self.jobs[handle] = lambda: (self.jobs.pop(handle, None), callback())[1]
        return handle

    def after_cancel(self, handle):
        self.jobs.pop(handle, None)


def test_responsive_grid_and_wrap_skip_duplicate_updates() -> None:
    container = _Container()
    cards = [_Card(), _Card()]
    label = _Label()

    assert responsive.apply_card_grid(container, cards, columns=2) is True
    assert responsive.apply_card_grid(container, cards, columns=2) is False
    assert [card.grid_calls for card in cards] == [1, 1]
    assert [card.forget_calls for card in cards] == [1, 1]

    assert responsive.set_wrap(label, 240) is True
    assert responsive.set_wrap(label, 240) is False
    assert label.wraps == [240]


def test_save_scheduler_debounces_and_flushes_once() -> None:
    app = _TimerApp()
    writes: list[str] = []

    save_scheduler.schedule(app, "ui_state", lambda: writes.append("save-1"))
    first_job = next(iter(app.jobs))
    save_scheduler.schedule(app, "ui_state", lambda: writes.append("save-2"))

    assert first_job not in app.jobs
    assert writes == []

    handle, callback = next(iter(app.jobs.items()))
    callback()

    assert handle not in app.jobs
    assert writes == ["save-2"]

    save_scheduler.schedule(app, "ui_state", lambda: writes.append("flush"))
    save_scheduler.flush(app, "ui_state")
    assert writes == ["save-2", "flush"]


def test_drain_queue_stops_polling_when_idle(monkeypatch) -> None:
    app = SimpleNamespace(_processing=False, _worker_process=None, _worker_queue=None, _queue_poll_handle="job-1")
    calls: list[str] = []
    monkeypatch.setattr(workflow, "_drain_worker_queue", lambda _app: calls.append("drain"))
    monkeypatch.setattr(workflow, "_check_worker_lifecycle", lambda _app: calls.append("check"))
    monkeypatch.setattr(queue_scheduler, "schedule", lambda _app: calls.append("schedule"))
    monkeypatch.setattr(queue_scheduler, "stop", lambda _app: calls.append("stop"))

    workflow.drain_queue(app)

    assert calls == ["drain", "check", "stop"]
    assert app._queue_poll_handle is None


def test_drain_queue_reschedules_only_while_worker_is_active(monkeypatch) -> None:
    app = SimpleNamespace(_processing=True, _worker_process=object(), _worker_queue=None, _queue_poll_handle="job-1")
    calls: list[str] = []
    monkeypatch.setattr(workflow, "_drain_worker_queue", lambda _app: calls.append("drain"))
    monkeypatch.setattr(workflow, "_check_worker_lifecycle", lambda _app: calls.append("check"))
    monkeypatch.setattr(queue_scheduler, "schedule", lambda _app: calls.append("schedule"))
    monkeypatch.setattr(queue_scheduler, "stop", lambda _app: calls.append("stop"))

    workflow.drain_queue(app)

    assert calls == ["drain", "check", "schedule"]
    assert app._queue_poll_handle is None
