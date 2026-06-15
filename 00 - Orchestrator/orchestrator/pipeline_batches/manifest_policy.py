from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def manifest_fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical["manifest_fingerprint"] = ""
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_dir(artifact_root: str | Path, pipeline_batch_id: str) -> Path:
    return Path(artifact_root) / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id


def pending_manifest_path(artifact_root: str | Path, pipeline_batch_id: str) -> Path:
    return manifest_dir(artifact_root, pipeline_batch_id) / "pending_pipeline_batch_manifest.json"


def final_manifest_path(artifact_root: str | Path, pipeline_batch_id: str) -> Path:
    return manifest_dir(artifact_root, pipeline_batch_id) / "pipeline_batch_manifest.json"
