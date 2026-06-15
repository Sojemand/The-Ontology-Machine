from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.ui import debug_repository
from orchestrator.ui.debug_actions import DebugHostAppActions

from .debug_host_descriptors import ROW_KEYS, descriptor as _descriptor, descriptors as _descriptors
from .debug_host_widgets import RowWidget, TextBox, Widget


def make_app(tmp_path: Path):
    module_widget = Widget("optimizer")
    mode_widget = Widget("single")
    after_callbacks: dict[str, object] = {}
    after_counter = {"value": 0}

    def after(_delay_ms: int, callback):
        after_counter["value"] += 1
        handle = f"after-{after_counter['value']}"
        after_callbacks[handle] = callback
        return handle

    def after_cancel(handle: str) -> None:
        after_callbacks.pop(handle, None)

    app = SimpleNamespace(
        _project_root=tmp_path,
        _state_dir=tmp_path / "state",
        _debug_state_path=tmp_path / "state" / "debug_host_state.json",
        _debug_descriptors=_descriptors(),
        _debug_module_var=module_widget,
        _debug_mode_var=mode_widget,
        _debug_module_menu=module_widget,
        _debug_mode_menu=mode_widget,
        _debug_input_entry=Widget(),
        _debug_source_entry=Widget(),
        _debug_format_entry=Widget(),
        _debug_doc_type_entry=Widget(),
        _debug_size_entry=Widget(),
        _debug_batch_entry=Widget("0"),
        _debug_worker_entry=Widget("1"),
        _debug_raw_entry=Widget(),
        _debug_raw_root_entry=Widget(),
        _debug_artifact_import_entry=Widget(),
        _debug_hash_var=SimpleNamespace(get=lambda: True, set=lambda _value: None),
        _debug_persist_page_images_var=SimpleNamespace(get=lambda: False, set=lambda _value: None),
        _debug_check_free_text_var=SimpleNamespace(get=lambda: True, set=lambda _value: None),
        _debug_check_context_scalars_var=SimpleNamespace(get=lambda: True, set=lambda _value: None),
        _debug_check_content_fields_var=SimpleNamespace(get=lambda: True, set=lambda _value: None),
        _debug_check_rows_var=SimpleNamespace(get=lambda: True, set=lambda _value: None),
        _debug_plan_label=Widget(),
        _debug_status_label=Widget(),
        _debug_detail_label=Widget(),
        _debug_metrics_label=Widget(),
        _debug_artifact_summary_label=Widget(),
        _debug_target_hint_label=Widget(),
        _debug_replay_status_label=Widget(),
        _debug_start_btn=Widget(),
        _debug_refresh_btn=Widget(),
        _debug_cancel_btn=Widget(),
        _debug_open_btn=Widget(),
        _debug_help_btn=Widget(),
        _debug_log_box=TextBox(),
        _debug_preview_box=TextBox(),
        _debug_replay_box=TextBox(),
        _debug_replay_load_file_btn=Widget(),
        _debug_replay_load_dir_btn=Widget(),
        _debug_replay_clear_btn=Widget(),
        _debug_artifact_buttons_frame=Widget(),
        _debug_control_rows={key: RowWidget() for key in ROW_KEYS},
        _debug_console_cards={key: RowWidget() for key in ("target", "advanced", "run_control")},
        _debug_console_grid=Widget(),
        _input_entry=Widget(),
        _debug_session=None,
        _debug_session_poll_handle=None,
        _hidden_debug_artifact_paths=set(),
        _debug_artifact_entries=[],
        _selected_debug_artifact_index=0,
        _scheduled_after_callbacks=after_callbacks,
        after=after,
        after_cancel=after_cancel,
    )
    app._current_debug_state = lambda: debug_repository.read_state(app)
    app._save_debug_state = lambda: debug_repository.save_state(app)
    app._flush_pending_saves = lambda: None
    app._flush_pending_save = lambda _key: None
    app._run_after = lambda handle: after_callbacks.pop(handle)()
    app._refresh_debug_session = lambda *, show_errors=True: DebugHostAppActions._refresh_debug_session(app, show_errors=show_errors)
    app._schedule_debug_session_poll = lambda: DebugHostAppActions._schedule_debug_session_poll(app)
    app._stop_debug_session_poll = lambda: DebugHostAppActions._stop_debug_session_poll(app)
    app._poll_debug_session = lambda: DebugHostAppActions._poll_debug_session(app)
    return app

