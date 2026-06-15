from __future__ import annotations

from pathlib import Path

TOP_LEVEL_SKIP_DIRS = {".venv", ".pytest_cache", ".tmp", "tests", "dev-tests", "dist", "installer", "__pycache__"}
EPHEMERAL_PREFIXES = (".pytest-tmp", ".pytest-basetemp", "pytest-cache-files-", "pytest-tmp-")


def matches_relative_path(relative_path: Path, patterns: tuple[str, ...]) -> bool:
    normalized = str(relative_path).replace("/", "\\")
    return any(normalized == pattern or normalized.startswith(f"{pattern}\\") for pattern in patterns)


def should_skip(
    relative_path: Path,
    *,
    mutable_dirs: tuple[str, ...],
    mutable_files: tuple[str, ...],
    excluded_runtime_paths: tuple[str, ...],
) -> bool:
    parts = relative_path.parts
    if not parts:
        return False
    return (
        parts[0] in TOP_LEVEL_SKIP_DIRS
        or _is_plugin_runtime(parts)
        or any(is_ephemeral_test_path_part(part) for part in parts)
        or matches_relative_path(relative_path, mutable_dirs)
        or matches_relative_path(relative_path, mutable_files)
        or _is_skipped_runtime_path(relative_path, parts, excluded_runtime_paths)
        or _is_skipped_config_or_database(relative_path, parts)
        or relative_path.suffix in {".pyc", ".pyo"}
        or "__pycache__" in parts
    )


def robocopy_exclusions(
    source_root: Path,
    *,
    mutable_dirs: tuple[str, ...],
    mutable_files: tuple[str, ...],
    excluded_runtime_paths: tuple[str, ...],
) -> tuple[list[str], list[str]]:
    exclude_dirs = [str(source_root / item) for item in sorted(TOP_LEVEL_SKIP_DIRS)]
    exclude_dirs.extend(
        [
            "__pycache__",
            ".pytest-local-tmp",
            ".pytest-tmp*",
            ".pytest-basetemp*",
            "pytest-cache-files-*",
            "pytest-tmp-*",
            relative_windows_path(source_root, "runtime\\wheelhouse-dev"),
        ]
    )
    exclude_dirs.extend(relative_windows_path(source_root, item) for item in mutable_dirs)
    exclude_dirs.extend(relative_windows_path(source_root, item) for item in excluded_runtime_paths)
    exclude_dirs.extend(plugin_runtime_dirs(source_root))
    exclude_files = [
        "*.pyc",
        "*.pyo",
        "corpus.db",
        "corpus.db-shm",
        "corpus.db-wal",
        relative_windows_path(source_root, "runtime\\wheelhouse.zip"),
        relative_windows_path(source_root, "config\\keystore.enc"),
        relative_windows_path(source_root, "config\\ui_state.json"),
    ]
    exclude_files.extend(relative_windows_path(source_root, item) for item in mutable_files)
    return exclude_dirs, exclude_files


def is_ephemeral_test_path_part(part: str) -> bool:
    return part == ".pytest-local-tmp" or any(part.startswith(prefix) for prefix in EPHEMERAL_PREFIXES)


def relative_windows_path(base_dir: Path, relative_path: str) -> str:
    parts = [part for part in relative_path.replace("/", "\\").split("\\") if part]
    return str(base_dir.joinpath(*parts))


def plugin_runtime_dirs(source_root: Path) -> list[str]:
    plugins_root = source_root / "plugins"
    if not plugins_root.exists():
        return []
    return [
        str(plugin_dir / runtime_dir)
        for plugin_dir in plugins_root.iterdir()
        if plugin_dir.is_dir()
        for runtime_dir in ("runtime", "venv", ".venv")
    ]


def _is_plugin_runtime(parts: tuple[str, ...]) -> bool:
    return len(parts) >= 3 and parts[0] == "plugins" and parts[2] in {"runtime", "venv", ".venv"}


def _is_skipped_runtime_path(relative_path: Path, parts: tuple[str, ...], excluded_runtime_paths: tuple[str, ...]) -> bool:
    return (
        (parts[0] == "runtime" and len(parts) > 1 and parts[1] == "wheelhouse-dev")
        or matches_relative_path(relative_path, excluded_runtime_paths)
        or (parts[0] == "runtime" and relative_path.name == "wheelhouse.zip")
    )


def _is_skipped_config_or_database(relative_path: Path, parts: tuple[str, ...]) -> bool:
    return (
        (parts[0] == "config" and relative_path.name in {"keystore.enc", "ui_state.json"})
        or relative_path.name in {"corpus.db", "corpus.db-shm", "corpus.db-wal"}
    )
