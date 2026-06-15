"""Actions mixin for the orchestrator debug-host tab."""

from __future__ import annotations

from .. import debug_host
from ..integrations.workflow import SubmodulePipelineModules
from . import debug_artifact_list, debug_help, debug_rendering, debug_repository, dialogs
from . import debug_actions_interactions, debug_actions_session


class DebugHostAppActions:
    _restore_debug_state = debug_actions_session.restore_debug_state
    _current_debug_state = debug_actions_session.current_debug_state
    _save_debug_state = debug_actions_session.save_debug_state
    _on_debug_change = debug_actions_session.on_debug_change
    _schedule_debug_state_save = debug_actions_session.schedule_debug_state_save
    _update_debug_button_state = debug_actions_session.update_debug_button_state
    _start_debug_session = debug_actions_session.start_debug_session
    _refresh_debug_session = debug_actions_session.refresh_debug_session
    _cancel_debug_session = debug_actions_session.cancel_debug_session
    _schedule_debug_session_poll = debug_actions_session.schedule_debug_session_poll
    _stop_debug_session_poll = debug_actions_session.stop_debug_session_poll
    _poll_debug_session = debug_actions_session.poll_debug_session
    _reset_debug_output = debug_actions_interactions.reset_debug_output
    _dismiss_debug_artifact = debug_actions_interactions.dismiss_debug_artifact
    _open_debug_artifacts = debug_actions_interactions.open_debug_artifacts
    _show_debug_help = debug_actions_interactions.show_debug_help
    _load_debug_artifact_file = debug_actions_interactions.load_debug_artifact_file
    _load_debug_artifact_dir = debug_actions_interactions.load_debug_artifact_dir
    _clear_debug_artifact_import = debug_actions_interactions.clear_debug_artifact_import
    _select_debug_artifact = debug_actions_interactions.select_debug_artifact
    _browse_debug_input = debug_actions_interactions.browse_debug_input
    _browse_debug_source = debug_actions_interactions.browse_debug_source
    _debug_launch_paths = debug_actions_interactions.debug_launch_paths
