"""Workflow stage for fallback-aware Optimizer path setup."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..models import atomic_text_write
from ..models.config import require_yaml_module
from ..models.validation import config_to_dict, validate_config_payload
from .policy import _build_layout, _fallback_home
from .types import PathLayout

_LEGACY_STATE_FILES = ("processed_hashes.json",)
_CONFIG_MIGRATIONS = (
    ("max_cell_text_length", 2000, 8000),
)


def resolve_layout(module_root_path: Path | None = None, app_home_path: Path | None = None) -> PathLayout:
    return _build_layout(module_root_path, app_home_path)


def ensure_app_layout(module_root_path: Path | None = None, app_home_path: Path | None = None) -> PathLayout:
    layout = resolve_layout(module_root_path, app_home_path)
    try:
        return _ensure_layout(layout)
    except OSError:
        if app_home_path is not None or layout.app_home == _fallback_home(module_root_path):
            raise
        return _ensure_layout(resolve_layout(module_root_path, _fallback_home(module_root_path)))


def ensure_module_layout(module_root_path: Path | None = None, app_home_path: Path | None = None) -> PathLayout:
    return ensure_app_layout(module_root_path, app_home_path)


def _ensure_layout(layout: PathLayout) -> PathLayout:
    for directory in (layout.config_dir, layout.state_dir, layout.output_dir, layout.log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    _seed_config_tree(layout)
    _migrate_legacy_state(layout)
    return layout


def _seed_config_tree(layout: PathLayout) -> None:
    if not layout.bundled_config_dir.exists():
        return
    for source in layout.bundled_config_dir.rglob("*"):
        relative = source.relative_to(layout.bundled_config_dir)
        target = layout.config_dir / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if relative == Path("config.yaml"):
            _seed_or_migrate_config(target, source)
            continue
        _seed_file(target, source)


def _migrate_legacy_state(layout: PathLayout) -> None:
    legacy_state_dir = layout.module_root / "state"
    if legacy_state_dir == layout.state_dir or not legacy_state_dir.exists():
        return
    for name in _LEGACY_STATE_FILES:
        source = legacy_state_dir / name
        if source.is_file():
            _seed_file(layout.state_dir / name, source)


def _seed_file(target: Path, source: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    try:
        with open(target, "xb") as handle:
            handle.write(data)
    except FileExistsError:
        return
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _seed_or_migrate_config(target: Path, source: Path) -> None:
    if not target.exists():
        _seed_file(target, source)
        return
    source_payload = _read_yaml_mapping(source)
    target_payload = _read_yaml_mapping(target)
    if not source_payload or not target_payload:
        return
    updated = dict(target_payload)
    changed = False
    for field_name, old_default, new_default in _CONFIG_MIGRATIONS:
        if updated.get(field_name) != old_default:
            continue
        if source_payload.get(field_name) != new_default:
            continue
        updated[field_name] = new_default
        changed = True
    if not changed:
        return
    normalized = config_to_dict(validate_config_payload(updated))
    atomic_text_write(target, _render_config_text(normalized))


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = require_yaml_module().safe_load(raw_text) or {}
        if isinstance(payload, Mapping):
            return dict(payload)
    except ModuleNotFoundError:
        pass
    except Exception:
        pass
    parsed: dict[str, object] = {}
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        token = value.split("#", 1)[0].strip().strip("'\"")
        lowered = token.lower()
        if lowered in {"true", "false"}:
            parsed[key.strip()] = lowered == "true"
            continue
        try:
            parsed[key.strip()] = int(token)
        except ValueError:
            parsed[key.strip()] = token
    return parsed


def _render_config_text(payload: dict[str, object]) -> str:
    try:
        return require_yaml_module().safe_dump(payload, sort_keys=False)
    except ModuleNotFoundError:
        return "".join(f"{key}: {value}\n" for key, value in payload.items())

