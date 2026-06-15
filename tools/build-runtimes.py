from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portable_runtime import ensure_portable_runtime, query_python_layout, runtime_python
from runtime_build_config import DEFAULT_MODULE_DIRS, ModuleBuildTarget
from runtime_build_default import build_client_frontend_runtime, build_default_runtime, prepare_portable_runtime
from runtime_build_entrypoints import maybe_build_plugins, resolve_targets, update_runtime_manifest
from runtime_build_libreoffice import (
    build_bundled_libreoffice_runtime,
    resolve_libreoffice_source_root,
)
from runtime_build_orchestrator import (
    build_orchestrator_runtime,
    sanity_check_orchestrator_runtime,
    validate_orchestrator_runtime,
)
from runtime_build_process import portable_runtime_env, run
from runtime_build_python import (
    ensure_host_pip,
    python_bits,
    resolve_orchestrator_base_python,
    resolve_runtime_base_python,
    runtime_python_candidates,
)
from runtime_build_records import runtime_validation_modules
from runtime_build_validation import validate_runtime_paths


def _run(*args, **kwargs):
    return run(*args, **kwargs)


def _portable_runtime_env(runtime_dir: Path) -> dict[str, str]:
    return portable_runtime_env(runtime_dir)


def _python_bits(python_exe: Path) -> int:
    return python_bits(python_exe, run_fn=_run)


def _runtime_python_candidates(requested_python: str | None) -> list[Path]:
    return runtime_python_candidates(requested_python, run_fn=_run, sys_platform=sys.platform)


def _resolve_runtime_base_python(requested_python: str | None, *, purpose: str = "Runtime") -> Path:
    return resolve_runtime_base_python(
        requested_python,
        purpose=purpose,
        sys_platform=sys.platform,
        candidates_fn=_runtime_python_candidates,
        query_layout_fn=query_python_layout,
        python_bits_fn=_python_bits,
    )


def _resolve_orchestrator_base_python(requested_python: str | None) -> Path:
    return resolve_orchestrator_base_python(
        requested_python,
        sys_platform=sys.platform,
        candidates_fn=_runtime_python_candidates,
        query_layout_fn=query_python_layout,
        python_bits_fn=_python_bits,
    )


def _resolve_libreoffice_source_root() -> Path:
    return resolve_libreoffice_source_root()


def _runtime_validation_modules(target: ModuleBuildTarget) -> list[str]:
    return runtime_validation_modules(target)


def _build_bundled_libreoffice_runtime(target: ModuleBuildTarget, *, clean: bool, validate_only: bool) -> None:
    build_bundled_libreoffice_runtime(
        target,
        clean=clean,
        validate_only=validate_only,
        run_fn=_run,
        resolve_source_root=_resolve_libreoffice_source_root,
    )


def _sanity_check_orchestrator_runtime(target: ModuleBuildTarget) -> None:
    sanity_check_orchestrator_runtime(
        target,
        run_fn=_run,
        env_fn=_portable_runtime_env,
        runtime_python_fn=runtime_python,
    )


def _prepare_portable_runtime(target: ModuleBuildTarget, *, base_python: Path, clean: bool, with_pip: bool) -> Path:
    return prepare_portable_runtime(target, base_python=base_python, clean=clean, with_pip=with_pip)


def _build_orchestrator_runtime(target: ModuleBuildTarget, *, clean: bool, archive_wheelhouse: bool, requested_python: str | None) -> None:
    build_orchestrator_runtime(
        target,
        clean=clean,
        archive_wheelhouse=archive_wheelhouse,
        requested_python=requested_python,
        resolve_python=_resolve_orchestrator_base_python,
        ensure_pip=ensure_host_pip,
        prepare_runtime=_prepare_portable_runtime,
        sanity_check=_sanity_check_orchestrator_runtime,
    )


def _build_default_runtime(target: ModuleBuildTarget, **kwargs) -> None:
    build_default_runtime(target, resolve_python=_resolve_runtime_base_python, **kwargs)


def _build_client_frontend_runtime(target: ModuleBuildTarget, **kwargs) -> None:
    build_client_frontend_runtime(target, resolve_python=_resolve_runtime_base_python, **kwargs)


def _build_module_runtime(target: ModuleBuildTarget, *, clean: bool, offline: bool, refresh_wheelhouse: bool, archive_wheelhouse: bool, requested_python: str | None, validate_only: bool) -> None:
    if target.is_orchestrator:
        if validate_only:
            ensure_portable_runtime(target.runtime_dir)
            validate_runtime_paths(target)
            _sanity_check_orchestrator_runtime(target)
        else:
            _build_orchestrator_runtime(target, clean=clean, archive_wheelhouse=archive_wheelhouse, requested_python=requested_python)
        return
    kwargs = dict(clean=clean, offline=offline, refresh_wheelhouse=refresh_wheelhouse, archive_wheelhouse=archive_wheelhouse, requested_python=requested_python, validate_only=validate_only)
    if target.is_client_frontend:
        _build_client_frontend_runtime(target, **kwargs)
    else:
        _build_default_runtime(target, **kwargs)
        _build_bundled_libreoffice_runtime(target, clean=clean, validate_only=validate_only)


def _resolve_targets(modules: list[str] | None) -> list[ModuleBuildTarget]:
    return resolve_targets(modules)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build bundled runtimes for Vision Pipeline modules.")
    parser.add_argument("--module", action="append", dest="modules", help="Module folder name under the pipeline root.")
    parser.add_argument("--no-clean", action="store_true", help="Reuse existing runtime directories when possible.")
    parser.add_argument("--offline", action="store_true", help="Use existing wheelhouses only; do not download packages.")
    parser.add_argument("--refresh-wheelhouse", action="store_true", help="Rebuild wheelhouses from requirements.txt before packaging.")
    parser.add_argument("--archive-wheelhouse", action="store_true", help="Compress wheelhouses after install for slimmer installer layouts.")
    parser.add_argument("--python", default="", help="Optional CPython 3.11 x64 executable for module core runtimes.")
    parser.add_argument("--skip-plugins", action="store_true", help="Skip module-specific plugin runtime builds.")
    parser.add_argument("--validate-only", action="store_true", help="Validate the existing runtime and wheelhouse without rebuilding them.")
    args = parser.parse_args(argv)
    for target in _resolve_targets(args.modules):
        if not target.root.exists():
            raise FileNotFoundError(f"Modulordner nicht gefunden: {target.root}")
        print(f"[BUILD] {target.root.name}")
        _build_module_runtime(target, clean=not args.no_clean, offline=args.offline, refresh_wheelhouse=args.refresh_wheelhouse, archive_wheelhouse=args.archive_wheelhouse, requested_python=args.python or None, validate_only=args.validate_only)
        update_runtime_manifest(target)
        maybe_build_plugins(target, skip_plugins=args.skip_plugins, offline=args.offline, archive_wheelhouse=args.archive_wheelhouse)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
