"""Thin public surface for the orchestrator pipeline engine."""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Callable

from ..bootstrap import ORCHESTRATOR_ROOT
from ..integrations.corpus_semantics import semantic_status as load_semantic_status
from ..integrations.taxonomy_blueprints import (
    export_default_blueprint_release as export_blueprint_release,
    list_default_blueprints as load_default_blueprints,
)
from ..integrations import PipelineModules, SubmodulePipelineModules
from ..models import PipelineSnapshot
from .. import policy_store
from ..state import load_pipeline_state
from . import database_workflow, embedding_workflow, release_workflow, reset_workflow, storage_repository, validation, workflow


class OrchestratorEngine:
    """Stateful pipeline runner with retry and error routing."""

    def __init__(
        self,
        *,
        orchestrator_root: Path | None = None,
        modules: PipelineModules | None = None,
        pipeline_state_path: Path | None = None,
        max_failed_attempts: int = 3,
        snapshot_callback: Callable[[PipelineSnapshot], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> None:
        self._root = Path(orchestrator_root or ORCHESTRATOR_ROOT)
        self._project_state_dir = self._root / "state"
        self._pipeline_state_override = Path(pipeline_state_path) if pipeline_state_path else None
        self._state_dir = storage_repository.pipeline_state_dir(self)
        self._runtime_root = self._state_dir / policy_store.run_workspace_dir_name()
        self._lock_path = self._project_state_dir / "orchestrator.lock"
        self._pipeline_state_path = Path(self._pipeline_state_override or (self._state_dir / "pipeline_state.json"))
        self._max_failed_attempts = max_failed_attempts
        self._snapshot_callback = snapshot_callback
        self._log_callback = log_callback
        self._cancel_requested = cancel_requested
        self._runtime_lock = threading.RLock()
        self._thread_local = threading.local()
        self._active_log_path: Path | None = None
        self._modules = modules or SubmodulePipelineModules(state_dir=self._project_state_dir)
        self._state = load_pipeline_state(self._pipeline_state_path)
        self._snapshot = PipelineSnapshot()

    @property
    def snapshot(self) -> PipelineSnapshot:
        return self._snapshot

    def close(self) -> None:
        self._modules.close()

    def build_pending_queue(self, ui_state):
        validation.ensure_valid_ui_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        storage_repository.reload_state(self)
        return workflow.build_pending_queue(self, ui_state)

    def run(self, ui_state, *, owner_input_hashes: set[str] | None = None):
        validation.ensure_valid_ui_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return workflow.run(self, ui_state, owner_input_hashes=owner_input_hashes)

    def activation_preflight(self, ui_state):
        validation.ensure_valid_release_activation_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return release_workflow.activation_preflight(self, ui_state)

    def activate_release(self, ui_state, *, confirmation_payload=None):
        validation.ensure_valid_release_activation_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return release_workflow.run_release_activation(
            self,
            ui_state,
            confirmation_payload=confirmation_payload,
        )

    def create_database(self, ui_state, *, request):
        validation.ensure_valid_create_database_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return database_workflow.run_create_database(self, ui_state, request=request)

    def list_default_blueprints(self):
        return load_default_blueprints(self._modules)

    def export_default_blueprint_release(self, *, blueprint_ref, target_locale=None, output_path):
        return export_blueprint_release(
            self._modules,
            blueprint_ref=str(blueprint_ref),
            target_locale=str(target_locale or "").strip() or None,
            output_path=Path(output_path),
        )

    def semantic_status(self, ui_state, *, corpus_db_path=None):
        validation.ensure_valid_create_database_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return load_semantic_status(
            self._modules,
            corpus_db_path=Path(corpus_db_path) if corpus_db_path is not None else storage_repository.corpus_db_path(ui_state),
        )

    def reset_run_history(self, ui_state):
        validation.ensure_valid_ui_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return reset_workflow.reset_run_history(self, ui_state)

    def reset_pipeline_logs(self, ui_state):
        return reset_workflow.reset_pipeline_logs(self, ui_state)

    def run_embeddings(self, ui_state):
        validation.ensure_valid_create_database_state(ui_state)
        storage_repository.configure_storage(self, ui_state)
        return embedding_workflow.run_embeddings(self, ui_state)
