from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..models.serialization import atomic_json_write


def artifact_ref(path: Path, root: Path) -> dict[str, str]:
    return {"artifact_path": path.relative_to(root).as_posix()}


def artifact_root_for_merge_manifest_root(manifest_root: str | Path) -> Path:
    root = Path(manifest_root)
    documents_root = root.parent.parent.parent
    if root.parent.name != "merge_runs" or root.parent.parent.name != "logs" or documents_root.name != "Documents":
        raise ValueError("merge manifest root must be under Documents/logs/merge_runs/<merge_run_id>.")
    return documents_root.parent


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload


def manifest_fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical["manifest_fingerprint"] = ""
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_manifest_root(target_artifact_root: str | Path, merge_run_id: str) -> Path:
    return Path(target_artifact_root) / "Documents" / "logs" / "merge_runs" / merge_run_id


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_manifest(path: str | Path, payload: Mapping[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_write(target, dict(payload), sort_keys=True, trailing_newline=True)
    return str(target)
