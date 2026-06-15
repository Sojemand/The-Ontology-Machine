from __future__ import annotations

# cspell:words nsetlocal

import json
import shutil
from pathlib import Path

from installer_stage import copy_release_tree
from all_in_one_config import (
    CLIENT_FRONTEND_IMMUTABLE_DIRS,
    CLIENT_FRONTEND_IMMUTABLE_FILES,
    CLIENT_FRONTEND_MODULE,
    DEFAULT_DEMO_DB_PATH,
    INSTALLER_ICON_FILES,
    MODULE_DIRS,
    PIPELINE_ROOT,
    ROOT_PAYLOAD_DIRS,
    all_in_one_config,
)
from all_in_one_texts import check_all_runtimes_batch, root_readme, uninstall_launcher_batch, uninstall_powershell


def reset_stage_dir(stage_dir: Path) -> None:
    ensure_inside_dist(stage_dir)
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)


def stage_module(module_name: str, stage_dir: Path) -> None:
    module_root = PIPELINE_ROOT / module_name
    if not module_root.exists():
        raise FileNotFoundError(f"Module folder missing: {module_root}")
    target_root = stage_dir / module_name
    if module_name == CLIENT_FRONTEND_MODULE:
        copy_client_frontend(module_root, target_root)
        return
    config = all_in_one_config(module_root)
    copy_release_tree(
        module_root,
        target_root,
        mutable_dirs=config.mutable_dirs,
        mutable_files=config.mutable_files,
        excluded_runtime_paths=config.excluded_runtime_paths,
    )


def stage_root_payloads(stage_dir: Path) -> None:
    for relative_dir in ROOT_PAYLOAD_DIRS:
        source = PIPELINE_ROOT / relative_dir
        if not source.exists():
            raise FileNotFoundError(f"Root payload folder missing: {source}")
        print(f"[STAGE] {relative_dir}")
        copy_root_payload_dir(source, stage_dir / relative_dir)


def copy_installer_icons(stage_dir: Path) -> None:
    source_dir = PIPELINE_ROOT / "installer" / "icons"
    target_dir = stage_dir / "icons"
    target_dir.mkdir(parents=True, exist_ok=True)
    for icon_name in INSTALLER_ICON_FILES:
        source = source_dir / icon_name
        if not source.exists():
            raise FileNotFoundError(f"Installer icon missing: {source}")
        shutil.copy2(source, target_dir / icon_name)


def write_root_launchers(stage_dir: Path) -> None:
    write_text(stage_dir / "Start Orchestrator.bat", '@echo off\nsetlocal EnableExtensions\ncall "%~dp000 - Orchestrator\\run.bat" %*\nexit /b %ERRORLEVEL%\n')
    write_text(stage_dir / "Start Client Frontend.bat", '@echo off\nsetlocal EnableExtensions\ncall "%~dp0Client Frontend\\start.bat" %*\nexit /b %ERRORLEVEL%\n')
    write_text(stage_dir / "Configure Client Frontend.bat", '@echo off\nsetlocal EnableExtensions\ncall "%~dp0Client Frontend\\config.bat" %*\nexit /b %ERRORLEVEL%\n')
    write_text(stage_dir / "Start Article Archive Extractor.bat", '@echo off\nsetlocal EnableExtensions\ncall "%~dp0Extractor_Tools\\Article Archive Extractor\\Start Article Archive Extractor.bat" %*\nexit /b %ERRORLEVEL%\n')
    write_text(stage_dir / "Start YouTube Transcript Extractor.bat", '@echo off\nsetlocal EnableExtensions\ncall "%~dp0Extractor_Tools\\YouTube Transcript Extractor\\Start YouTube Transcript Extractor.bat" %*\nexit /b %ERRORLEVEL%\n')
    write_text(stage_dir / "Start Audio Transcription Extractor.bat", '@echo off\nsetlocal EnableExtensions\ncall "%~dp0Extractor_Tools\\Audio Transcription Extractor\\Start Audio Transcription Extractor.bat" %*\nexit /b %ERRORLEVEL%\n')
    write_text(stage_dir / "Check All Runtimes.bat", check_all_runtimes_batch())
    write_text(stage_dir / "Uninstall Ontology Machine.bat", uninstall_launcher_batch())
    write_text(stage_dir / "Uninstall Ontology Machine.ps1", uninstall_powershell())
    write_text(stage_dir / "README.txt", root_readme())


def write_release_manifest(stage_dir: Path, *, app_version: str) -> None:
    payload = {
        "bundle": "Ontology Machine",
        "app_version": app_version,
        "modules": list(MODULE_DIRS),
        "root_payload_dirs": list(ROOT_PAYLOAD_DIRS),
        "sample_databases": [{"name": "Consciousness Travel - Default Demo", "database_path": DEFAULT_DEMO_DB_PATH}],
        "entry_points": [
            "Start Orchestrator.bat",
            "Start Client Frontend.bat",
            "Configure Client Frontend.bat",
            "Start Article Archive Extractor.bat",
            "Start YouTube Transcript Extractor.bat",
            "Start Audio Transcription Extractor.bat",
            "Uninstall Ontology Machine.bat",
        ],
    }
    (stage_dir / "release-manifest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_inside_dist(path: Path) -> None:
    resolved = path.resolve()
    dist_root = (PIPELINE_ROOT / "dist").resolve()
    if not resolved.is_relative_to(dist_root):
        raise ValueError(f"Refusing to remove path outside dist: {resolved}")


def copy_client_frontend(module_root: Path, target_root: Path) -> None:
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)
    for relative_dir in CLIENT_FRONTEND_IMMUTABLE_DIRS:
        copy_dir(module_root / relative_dir, target_root / relative_dir)
    for relative_file in CLIENT_FRONTEND_IMMUTABLE_FILES:
        copy_file(module_root / relative_file, target_root / relative_file)


def copy_file(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Required frontend release file missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_dir(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Required frontend release directory missing: {source}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def copy_root_payload_dir(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Required root payload directory missing: {source}")
    validate_root_payload_sqlite_sidecars(source)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        if should_skip_root_payload_path(relative):
            continue
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if should_skip_root_payload_file(item):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)


def validate_root_payload_sqlite_sidecars(source: Path) -> None:
    dirty_wal = next((path for path in source.rglob("*.db-wal") if path.stat().st_size > 0), None)
    if dirty_wal is not None:
        raise RuntimeError(
            "Root payload contains a non-empty SQLite WAL sidecar. "
            f"Checkpoint the database before staging: {dirty_wal}"
        )


def should_skip_root_payload_file(path: Path) -> bool:
    if path.name.endswith(".db-shm"):
        return True
    if path.name.endswith(".db-wal"):
        return True
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return True
    return False


def should_skip_root_payload_path(relative: Path) -> bool:
    ignored_parts = {".venv", "__pycache__", ".pytest_cache"}
    return any(part in ignored_parts for part in relative.parts)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\r\n")
