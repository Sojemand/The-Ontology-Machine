"""Repository stage for mutable runtime directories and config seeding."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .types import PathLayout

_LEGACY_SKIP_ROW_FIELDS = ["_source_refs"]
_LEGACY_ROW_ANCHOR_KEYS = ["position", "description", "label", "item", "title", "name"]


def ensure_app_layout(layout: PathLayout) -> Path:
    for directory in (layout.config_dir, layout.state_dir, layout.output_dir, layout.log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    if not layout.default_config_path.exists() and layout.bundled_config_path.exists():
        _seed_default_file(layout.default_config_path, layout.bundled_config_path)
    elif layout.default_config_path.exists() and layout.bundled_config_path.exists():
        _migrate_default_config(layout.default_config_path, layout.bundled_config_path)
    return layout.app_home


def _seed_default_file(target: Path, source: Path) -> None:
    if target.exists():
        return

    _atomic_write_bytes(target, source.read_bytes(), replace_existing=False)


def _migrate_default_config(target: Path, source: Path) -> None:
    try:
        target_payload = json.loads(target.read_text(encoding="utf-8"))
        source_payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(target_payload, dict) or not isinstance(source_payload, dict):
        return

    target_match = target_payload.get("match")
    source_match = source_payload.get("match")
    if not isinstance(target_match, dict) or not isinstance(source_match, dict):
        return

    changed = False
    if target_match.get("skip_row_fields") == _LEGACY_SKIP_ROW_FIELDS:
        new_skip_fields = source_match.get("skip_row_fields")
        if isinstance(new_skip_fields, list) and new_skip_fields != _LEGACY_SKIP_ROW_FIELDS:
            target_match["skip_row_fields"] = new_skip_fields
            changed = True
    if target_match.get("row_anchor_keys") == _LEGACY_ROW_ANCHOR_KEYS:
        new_anchor_keys = source_match.get("row_anchor_keys")
        if isinstance(new_anchor_keys, list) and new_anchor_keys != _LEGACY_ROW_ANCHOR_KEYS:
            target_match["row_anchor_keys"] = new_anchor_keys
            changed = True
    if changed:
        _atomic_write_json(target, target_payload)


def _atomic_write_json(target: Path, payload: dict[str, object]) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    _atomic_write_bytes(target, data)


def _atomic_write_bytes(target: Path, data: bytes, *, replace_existing: bool = True) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix="cfg-", suffix=".tmp", delete=False) as handle:
        handle.write(data)
        temp_path = Path(handle.name)
    try:
        if replace_existing:
            temp_path.replace(target)
        else:
            try:
                temp_path.rename(target)
            except (FileExistsError, PermissionError):
                if target.exists():
                    return
                raise
    finally:
        temp_path.unlink(missing_ok=True)
