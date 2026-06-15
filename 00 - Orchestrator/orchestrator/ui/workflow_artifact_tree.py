"""Artifact-tree creation workflow for Orchestrator UI actions."""

from __future__ import annotations

from pathlib import Path
import re
from uuid import uuid4

from ..models import utc_now_iso
from ..workspace_domain import create_artifact_tree as create_kernel_artifact_tree
from ..workspace_domain.types import KERNEL_ARTIFACT_TREE_VERSION
from ..workspace_domain.validation import request_fingerprint as workspace_request_fingerprint
from . import dialogs, repository


def create_artifact_tree(app) -> None:
    if app._processing:
        return
    app._flush_pending_saves()
    fields = repository.read_fields(app)
    initial_parent, initial_name = _suggest_artifact_tree_dialog_values(fields)
    try:
        dialog_result = dialogs.prompt_create_artifact_tree(app, initial_parent=initial_parent, initial_name=initial_name)
        if not dialog_result:
            return
        response = create_kernel_artifact_tree(_build_create_artifact_tree_request(dialog_result))
        refs = _artifact_tree_refs(response)
        _apply_artifact_tree_refs(app, refs)
        app._append_log(f"[TREE] Artifact Tree ready: {refs['artifact_root_path']}")
    except Exception as exc:
        app._append_log(f"[ERROR] Artifact Tree could not be created: {exc}")
        dialogs.show_error(str(exc))


def _build_create_artifact_tree_request(dialog_result: dict[str, str]) -> dict[str, object]:
    parent = _artifact_tree_parent(dialog_result.get("artifact_root_parent", ""))
    name = _artifact_tree_name(dialog_result.get("artifact_root_name", ""))
    payload: dict[str, object] = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "create_artifact_tree",
        "workflow_run_id": f"orch_ui_{uuid4().hex}",
        "adapter_call_id": f"adc_{uuid4().hex}",
        "requested_at": utc_now_iso(),
        "artifact_root_parent": str(parent),
        "artifact_root_name": name,
        "create_mode": "idempotent_create",
        "folder_contract_version": KERNEL_ARTIFACT_TREE_VERSION,
        "target_identity": {},
    }
    payload["request_fingerprint"] = workspace_request_fingerprint(payload)
    return payload


def _apply_artifact_tree_refs(app, refs: dict[str, str]) -> None:
    repository.set_entry_path(app, app._input_entry, refs["input_path"])
    repository.set_entry_path(app, app._artifact_entry, refs["artifact_root_path"])
    repository.set_entry_path(app, app._corpus_entry, refs["corpus_path"])
    if hasattr(app, "_selected_db_entry"):
        repository.set_entry_path(app, app._selected_db_entry, str(Path(refs["corpus_path"]) / "corpus.db"))
    if hasattr(app, "_semantic_release_mode_selector"):
        app._semantic_release_mode_selector.set("DB Release")
    elif hasattr(app, "_semantic_release_mode_var"):
        app._semantic_release_mode_var.set("DB Release")
    app._ui_state = repository.current_ui_state(app)
    app._save_ui_state()
    app._refresh_database_status()
    app._update_button_state()


def _artifact_tree_refs(response: dict[str, object]) -> dict[str, str]:
    raw_refs = response.get("output_refs")
    if not isinstance(raw_refs, dict):
        raise ValueError("Artifact Tree response does not contain output_refs.")
    refs = {key: str(raw_refs.get(key) or "").strip() for key in ("artifact_root_path", "input_path", "corpus_path", "semantic_release_path")}
    missing = [key for key, value in refs.items() if not value]
    if missing:
        raise ValueError(f"Artifact Tree response incomplete: {', '.join(missing)}")
    return refs


def _suggest_artifact_tree_dialog_values(fields) -> tuple[str, str]:
    artifact_text = str(fields.artifact_folder or "").strip()
    if artifact_text:
        artifact_path = Path(artifact_text)
        return str(artifact_path.parent), artifact_path.name or "Artifact Tree"
    for folder_text, canonical_name in ((fields.input_folder, "Input"), (fields.corpus_output_folder, "Corpus")):
        text = str(folder_text or "").strip()
        if not text:
            continue
        path = Path(text)
        if path.name == canonical_name and path.parent.name:
            return str(path.parent.parent), path.parent.name
    return str(Path.home()), "Artifact Tree"


def _artifact_tree_parent(value: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Parent folder must not be empty.")
    return Path(text).expanduser()


def _artifact_tree_name(value: str) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("Tree name must not be empty.")
    if name in {".", ".."} or re.search(r'[<>:"/\\\\|?*]', name) or name.endswith("."):
        raise ValueError("Tree name is not a valid folder name.")
    return name
