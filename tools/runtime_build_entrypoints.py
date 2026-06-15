from __future__ import annotations

import contextlib
import sys

from runtime_build_config import DEFAULT_MODULE_DIRS, PIPELINE_ROOT, ModuleBuildTarget
from runtime_build_process import run


def build_plugins(target: ModuleBuildTarget, *, offline: bool, archive_wheelhouse: bool) -> None:
    for bootstrap_path in target.plugin_bootstraps:
        command = [str(sys.executable), str(bootstrap_path), "bootstrap", "--plugin-dir", str(bootstrap_path.parent)]
        if offline:
            command.append("--offline")
        if archive_wheelhouse:
            command.append("--archive-wheelhouse")
        run(command, cwd=bootstrap_path.parent)


def update_runtime_manifest(target: ModuleBuildTarget) -> None:
    hook = target.runtime_manifest_hook
    if hook is not None:
        run([str(sys.executable), str(hook), "--write-runtime-manifest"], cwd=target.root)


def resolve_targets(modules: list[str] | None) -> list[ModuleBuildTarget]:
    module_names = modules or list(DEFAULT_MODULE_DIRS)
    return [ModuleBuildTarget(PIPELINE_ROOT / module_name) for module_name in module_names]


def maybe_build_plugins(target: ModuleBuildTarget, *, skip_plugins: bool, offline: bool, archive_wheelhouse: bool) -> None:
    if skip_plugins:
        return
    with contextlib.suppress(FileNotFoundError):
        build_plugins(target, offline=offline, archive_wheelhouse=archive_wheelhouse)
