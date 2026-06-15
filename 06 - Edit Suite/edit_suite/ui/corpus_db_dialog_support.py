"""Non-visual helpers for the new corpus DB dialog."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from ..repository import atomic_json_write
from .. import validation

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def resolve_corpus_root(app, payload: dict) -> Path:
    pipeline_root = _pipeline_root(app)
    if pipeline_root is not None:
        configured = _configured_corpus_root(pipeline_root)
        if configured is not None:
            return configured
    corpus_db_path = str(payload.get("corpus_db_path") or "").strip()
    if corpus_db_path:
        return Path(corpus_db_path).expanduser().resolve().parent
    entry = app._selected_entry()
    return (Path(entry.module_root) / "output").resolve()


def default_locale(app, surface_id: str, dialog_config: dict, locale_options: tuple[str, ...]) -> str:
    module_context = get_module_context(app)
    persisted = str(module_context.get(str(dialog_config.get("locale_persist_key") or "new_corpus_db_taxonomy_locale")) or "").strip()
    if persisted:
        return persisted
    surface = (app._action_widgets.get(surface_id) or {}).get("surface")
    draft = dict(getattr(surface, "draft", {}) or {})
    release_locale = str(draft.get("default_runtime_locale") or draft.get("default_authoring_locale") or "").strip()
    if release_locale:
        return release_locale
    configured = str(dialog_config.get("default_locale") or "").strip()
    if configured:
        return configured
    return locale_options[0] if locale_options else "de"


def locale_options(dialog_config: dict) -> tuple[str, ...]:
    raw = dialog_config.get("locale_options")
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    for item in raw:
        value = str(item.get("value") or item.get("label") or "").strip() if isinstance(item, dict) else str(item).strip()
        if value:
            values.append(value)
    return tuple(values)


def get_module_context(app) -> dict:
    contexts = app._ui_state.setdefault("operation_contexts", {})
    current = contexts.get(app._selected_module)
    if not isinstance(current, dict):
        current = {}
        contexts[app._selected_module] = current
    return current


def build_filename(label: str, locale: str) -> str:
    return validation.safe_filename(f"{label}-{date.today().isoformat()}-corpus-{locale}.db", fallback=f"corpus-{locale}.db")


def safe_segment(value: str, *, fallback: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("-", str(value or "").strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("._-")
    return validation.safe_filename(cleaned, fallback=fallback)


def has_tk(app) -> bool:
    return bool(object.__getattribute__(app, "__dict__").get("tk")) and callable(getattr(app, "wait_window", None))


def write_confirmation_artifact(app, surface_id: str, *, action: str, database_label: str, taxonomy_locale: str) -> Path:
    artifact_dir = validation.ensure_state_child(
        app._state_root,
        app._state_root / "corpus-db-confirmations" / safe_name(app._selected_module) / safe_name(surface_id),
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = validation.safe_filename(f"{safe_name(action or 'create_new_corpus_db')}.json", fallback="create_new_corpus_db.json")
    artifact_path = validation.ensure_state_child(app._state_root, artifact_dir / artifact_name)
    payload = {
        "artifact_version": "new_corpus_db_confirmation_v1",
        "requested_action": action,
        "confirmed": True,
        "database_label": str(database_label).strip(),
        "taxonomy_locale": str(taxonomy_locale).strip().lower(),
        "created_on": date.today().isoformat(),
    }
    atomic_json_write(artifact_path, payload)
    return artifact_path


def safe_name(value: str) -> str:
    safe = str(value or "").replace("/", ".").replace("\\", ".").replace(" ", "_")
    for char in ':*?"<>|':
        safe = safe.replace(char, "_")
    return validation.safe_filename(safe, fallback="segment")


def _pipeline_root(app) -> Path | None:
    raw = str(getattr(app, "_pipeline_root", "") or "").strip()
    return Path(raw).resolve() if raw else None


def _configured_corpus_root(pipeline_root: Path) -> Path | None:
    orchestrator_state = pipeline_root / "00 - Orchestrator" / "state" / "ui_state.json"
    if not orchestrator_state.exists():
        return None
    try:
        data = json.loads(orchestrator_state.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    artifact_folder = str(data.get("artifact_folder") or "").strip()
    corpus_output_folder = str(data.get("corpus_output_folder") or "").strip()
    if artifact_folder:
        return (Path(artifact_folder) / "Corpus").resolve()
    if corpus_output_folder:
        return Path(corpus_output_folder).expanduser().resolve()
    return None
