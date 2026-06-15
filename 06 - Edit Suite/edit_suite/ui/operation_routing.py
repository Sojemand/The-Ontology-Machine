"""Routing helpers for owner actions that run through another module."""
from __future__ import annotations

import json
from pathlib import Path


def action_target(app, entry, action_link: dict, payload: dict) -> tuple[Path, str, dict]:
    if not runs_via_orchestrator(action_link):
        return Path(entry.module_root), str(action_link.get("contract_module") or ""), payload
    orchestrator_root = orchestrator_root_for(app, selected_entry=entry)
    return (
        orchestrator_root,
        "orchestrator.orchestrator_contract",
        orchestrator_payload(orchestrator_root, Path(entry.module_root), action_link, payload),
    )


def runs_via_orchestrator(action_link: dict) -> bool:
    owner = str(action_link.get("runtime_owner") or action_link.get("route_via") or "").strip().casefold()
    if owner == "orchestrator":
        return True
    if str(action_link.get("orchestrator_action") or "").strip():
        return True
    return False


def orchestrator_root_for(app, *, selected_entry) -> Path:
    snapshot = getattr(app, "_snapshot", None)
    for entry in getattr(snapshot, "entries", ()) or ():
        if str(getattr(entry, "module_key", "") or "").strip() == "orchestrator":
            return Path(entry.module_root)
    pipeline_root = Path(str(getattr(app, "_pipeline_root", "") or Path(selected_entry.module_root).parent))
    candidate = pipeline_root / "00 - Orchestrator"
    if (candidate / "module-manifest.json").exists():
        return candidate
    raise ValueError("Orchestrator module not found in the Edit Suite registry.")


def orchestrator_payload(orchestrator_root: Path, selected_module_root: Path, action_link: dict, payload: dict) -> dict:
    action = str(action_link.get("orchestrator_action") or "").strip()
    if not action and str(action_link.get("action") or "").strip() == "generate_embeddings":
        action = "embeddings"
    if action == "embeddings":
        return {"action": action, "ui_state": embedding_ui_state(orchestrator_root, selected_module_root, payload)}
    raise ValueError(f"Orchestrator action is missing or unsupported: {action or '<empty>'}")


def embedding_ui_state(orchestrator_root: Path, selected_module_root: Path, payload: dict) -> dict:
    state_path = orchestrator_root / "state" / "ui_state.json"
    if not state_path.exists():
        raise ValueError(f"Orchestrator UI state is missing: {state_path}")
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Orchestrator UI state is invalid: {state_path}")
    corpus_db_path = payload_db_path(payload.get("corpus_db_path"), selected_module_root)
    if corpus_db_path is not None:
        data["selected_corpus_db_path"] = str(corpus_db_path)
        data["corpus_output_folder"] = str(corpus_db_path.parent)
        if not str(data.get("artifact_folder") or "").strip():
            data["artifact_folder"] = str(corpus_db_path.parent.parent)
    return data


def payload_db_path(value, selected_module_root: Path) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = selected_module_root / candidate
    return candidate.resolve(strict=False)
