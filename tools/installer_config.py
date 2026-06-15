from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SCRIPT_NAME = "CorpusBuilderVision.iss"
DEFAULT_MUTABLE_DIRS = ("output", "runtime\\state")
DEFAULT_MUTABLE_FILES: tuple[str, ...] = ()
DEFAULT_EXCLUDED_RUNTIME_PATHS = ("runtime\\wheelhouse", "runtime\\state")
DEFAULT_SIGN_TARGETS: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstallerConfig:
    script_name: str = DEFAULT_SCRIPT_NAME
    mutable_dirs: tuple[str, ...] = DEFAULT_MUTABLE_DIRS
    mutable_files: tuple[str, ...] = DEFAULT_MUTABLE_FILES
    excluded_runtime_paths: tuple[str, ...] = DEFAULT_EXCLUDED_RUNTIME_PATHS
    sign_targets: tuple[str, ...] = DEFAULT_SIGN_TARGETS


def _coerce_list(payload: dict[str, object], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = payload.get(key, list(default))
    if not isinstance(raw_value, list):
        raise ValueError(f"{key} muss ein Array sein.")
    values = []
    for item in raw_value:
        value = str(item).strip().replace("/", "\\")
        if value:
            values.append(value)
    return tuple(values)


def load_installer_config(module_root: Path) -> InstallerConfig:
    manifest_path = module_root / "installer" / "installer-manifest.json"
    if not manifest_path.exists():
        return InstallerConfig()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"installer-manifest.json muss ein JSON-Objekt sein: {manifest_path}")

    script_name = str(payload.get("script_name") or DEFAULT_SCRIPT_NAME).strip() or DEFAULT_SCRIPT_NAME
    return InstallerConfig(
        script_name=script_name,
        mutable_dirs=_coerce_list(payload, "mutable_dirs", DEFAULT_MUTABLE_DIRS),
        mutable_files=_coerce_list(payload, "mutable_files", DEFAULT_MUTABLE_FILES),
        excluded_runtime_paths=_coerce_list(
            payload,
            "excluded_runtime_paths",
            DEFAULT_EXCLUDED_RUNTIME_PATHS,
        ),
        sign_targets=_coerce_list(payload, "sign_targets", DEFAULT_SIGN_TARGETS),
    )
