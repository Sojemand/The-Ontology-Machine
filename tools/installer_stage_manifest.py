from __future__ import annotations

import json
from pathlib import Path


def write_release_manifest(
    module_root: Path,
    staging_dir: Path,
    *,
    app_version: str,
    mutable_dirs: tuple[str, ...],
    mutable_files: tuple[str, ...],
    excluded_runtime_paths: tuple[str, ...],
    sign_targets: tuple[str, ...],
) -> None:
    payload = {
        "module": module_root.name,
        "app_version": app_version,
        "staging_dir": str(staging_dir),
        "mutable_dirs": list(mutable_dirs),
        "mutable_files": list(mutable_files),
        "excluded_runtime_paths": list(excluded_runtime_paths),
        "sign_targets": list(sign_targets),
    }
    (staging_dir / "release-manifest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
