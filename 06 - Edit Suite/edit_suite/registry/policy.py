"""Discovery policy for sibling modules."""

from __future__ import annotations

import os
import re
from pathlib import Path

MODULE_DIR_RE = re.compile(r"^\d{2}[a-z]?\s-\s")
MODULE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
EXCLUDED_DIRS = {"06 - Edit Suite", "Client Frontend"}
IGNORED_NAMES = {".pytest_cache", ".tmp", "__pycache__", "dist", "state", ".venv", "venv"}
REQUIRED_CONTRACT_ACTIONS = ("describe_surfaces", "read_surface", "validate_surface", "write_surface")
REGISTRY_PROBE_MAX_WORKERS = 4


def candidate_dirs(pipeline_root: Path) -> list[Path]:
    candidates = [
        path
        for path in pipeline_root.iterdir()
        if path.is_dir() and MODULE_DIR_RE.match(path.name) and path.name not in EXCLUDED_DIRS
    ]
    candidates.sort(key=lambda path: path.name.casefold())
    return candidates


def is_placeholder_dir(module_root: Path) -> bool:
    entries = [entry.name for entry in module_root.iterdir() if entry.name not in IGNORED_NAMES and not entry.name.startswith(".")]
    return not entries


def _is_supported_contract_path(module_root: Path, contract_path: Path) -> bool:
    relative_parts = contract_path.relative_to(module_root).parts
    for part in relative_parts[:-1]:
        if part in {"runtime", "dist", "dev-tests"}:
            return False
        if part in IGNORED_NAMES or part.startswith("."):
            return False
    return True


def _should_descend(module_root: Path, path: Path) -> bool:
    relative_parts = path.relative_to(module_root).parts
    for part in relative_parts:
        if part in {"runtime", "dist", "dev-tests"}:
            return False
        if part in IGNORED_NAMES or part.startswith("."):
            return False
    return True


def _iter_contract_dirs(module_root: Path):
    stack = [module_root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                children: list[Path] = []
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    child = Path(entry.path)
                    if child.name == "edit_contract":
                        yield child
                        continue
                    if _should_descend(module_root, child):
                        children.append(child)
        except OSError:
            continue
        children.sort(key=lambda path: path.name.casefold(), reverse=True)
        stack.extend(children)


def manifest_contract_candidate(module_root: Path, manifest: dict) -> Path | None:
    for module_name in _manifest_contract_modules(manifest):
        candidate = module_root.joinpath(*module_name.split("."))
        if candidate.exists() and _is_supported_contract_path(module_root, candidate):
            return candidate
    return None


def _manifest_contract_modules(manifest: dict):
    edit_contract_module = str(manifest.get("edit_contract_module") or "").strip()
    if _is_module_name(edit_contract_module):
        yield edit_contract_module
    launcher_module = str(manifest.get("launcher_module") or "").strip()
    if _is_module_name(launcher_module):
        yield f"{launcher_module}.edit_contract"


def _is_module_name(value: str) -> bool:
    if not value:
        return False
    return all(MODULE_NAME_RE.match(part) for part in value.split("."))


def contract_candidates(module_root: Path) -> list[Path]:
    results: list[Path] = []
    for path in _iter_contract_dirs(module_root):
        if not _is_supported_contract_path(module_root, path):
            continue
        results.append(path)
    return sorted(
        results,
        key=lambda path: (len(path.relative_to(module_root).parts), str(path.relative_to(module_root)).casefold()),
    )
