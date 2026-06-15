"""Session lifecycle helpers for the orchestrator debug-host tab."""

from __future__ import annotations

from .. import debug_host
from ..integrations.workflow import SubmodulePipelineModules
from . import debug_artifact_list, debug_rendering, debug_repository, dialogs

_DEBUG_SESSION_POLL_INTERVAL_MS = 300


def restore_debug_state(self) -> None:
    debug_artifact_list.reset_hidden_paths(self)
    debug_repository.restore_state(self)
    apply_debug_view(self, scope="full")


def current_debug_state(self):
    return debug_repository.read_state(self)


def save_debug_state(self):
    return debug_repository.save_state(self)


def on_debug_change(self) -> None:
    if getattr(self, "_suspend_surface_events", False):
        return
    self._schedule_debug_state_save()
    apply_debug_view(self, scope="controls")


def schedule_debug_state_save(self) -> None:
    from . import save_scheduler

    save_scheduler.schedule(self, "debug_state", self._save_debug_state)


def update_debug_button_state(self) -> None:
    debug_rendering.update_buttons(self)


def start_debug_session(self) -> None:
    self._flush_pending_saves()
    state = self._save_debug_state()
    descriptor = debug_repository.descriptor_for_state(self, state)
    plan = debug_repository.plan_for_state(self, state, descriptor=descriptor)
    try:
        self._stop_debug_session_poll()
        debug_artifact_list.reset_hidden_paths(self)
        input_root, source_path = self._debug_launch_paths(state, descriptor)
        self._debug_session = debug_host.start(
            str(state["module_key"]),
            str(state["mode"]),
            input_root,
            source_path=source_path,
            state_root=self._state_dir,
            registry_path=self._project_root / "module-registry.json",
            options=debug_repository.runtime_options(state, descriptor=descriptor),
            descriptor=descriptor,
            plan=plan,
            modules=SubmodulePipelineModules(state_dir=self._state_dir),
        )
        self._selected_debug_artifact_index = 0
        apply_debug_view(self, scope="full")
        self._schedule_debug_session_poll()
    except Exception as exc:
        dialogs.show_error(str(exc))


def refresh_debug_session(self, *, show_errors: bool = True) -> None:
    if self._debug_session is None:
        return
    try:
        self._debug_session = debug_host.refresh(
            self._debug_session,
            modules=SubmodulePipelineModules(state_dir=self._state_dir),
        )
        apply_debug_view(self, scope="full")
        if debug_session_running(self._debug_session):
            self._schedule_debug_session_poll()
        else:
            self._stop_debug_session_poll()
    except Exception as exc:
        self._stop_debug_session_poll()
        if show_errors:
            dialogs.show_error(str(exc))


def cancel_debug_session(self) -> None:
    if self._debug_session is None:
        return
    self._debug_session = debug_host.cancel(self._debug_session)
    apply_debug_view(self, scope="full")
    if debug_session_running(self._debug_session):
        self._schedule_debug_session_poll()
    else:
        self._stop_debug_session_poll()


def schedule_debug_session_poll(self) -> None:
    if (
        getattr(self, "_debug_session_poll_handle", None) is not None
        or not hasattr(self, "after")
        or not debug_session_running(getattr(self, "_debug_session", None))
    ):
        return
    self._debug_session_poll_handle = self.after(_DEBUG_SESSION_POLL_INTERVAL_MS, self._poll_debug_session)


def stop_debug_session_poll(self) -> None:
    handle = getattr(self, "_debug_session_poll_handle", None)
    if handle is not None and hasattr(self, "after_cancel"):
        try:
            self.after_cancel(handle)
        except Exception:
            pass
    self._debug_session_poll_handle = None


def poll_debug_session(self) -> None:
    self._debug_session_poll_handle = None
    if self._debug_session is None:
        return
    if not debug_session_running(self._debug_session):
        apply_debug_view(self, scope="full")
        return
    self._refresh_debug_session(show_errors=False)


def debug_session_running(session) -> bool:
    return bool(
        session is not None
        and session.active_step is not None
        and (session.result is None or session.result.status not in {"ok", "error", "cancelled"})
    )


def apply_debug_view(app, *, scope: str) -> None:
    try:
        debug_rendering.apply_view(app, scope=scope)
    except TypeError:
        debug_rendering.apply_view(app)
