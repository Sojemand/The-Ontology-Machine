from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from .path_io import as_os_path, read_json as _read_json


def read_json(path: str | Path) -> dict[str, Any]:
    return _read_json(path)


def batch_manifest_root(artifact_root: str | Path) -> Path:
    return Path(artifact_root) / "Documents" / "logs" / "pipeline_batches"


def list_finalized_manifests(artifact_root: str | Path) -> list[Path]:
    root = batch_manifest_root(artifact_root)
    if not os.path.isdir(as_os_path(root)):
        return []
    manifests: list[tuple[float, Path]] = []
    with os.scandir(as_os_path(root)) as entries:
        for entry in entries:
            if not entry.is_dir():
                continue
            manifest_path = Path(entry.path) / "pipeline_batch_manifest.json"
            if os.path.isfile(as_os_path(manifest_path)):
                manifests.append(
                    (
                        os.path.getmtime(as_os_path(manifest_path)),
                        Path(str(manifest_path).replace("\\\\?\\UNC\\", "\\\\").replace("\\\\?\\", "")),
                    )
                )
    return [path for _, path in sorted(manifests, key=lambda item: item[0], reverse=True)]


def latest_manifest(artifact_root: str | Path) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    manifests = list_finalized_manifests(artifact_root)
    if not manifests:
        return None, None
    path = manifests[0]
    return read_json(path), path
