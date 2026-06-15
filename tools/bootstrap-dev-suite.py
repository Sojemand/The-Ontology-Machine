from __future__ import annotations

import argparse
import json
from pathlib import Path

from bootstrap_dev_install import ensure_pip, pip_command, run_import_preflight
from bootstrap_dev_python import resolve_python_exe, write_python_path_file, write_python_path_overlay
from bootstrap_dev_runtime import clean_host_binding_files, copy_runtime_tree, run


def _load_suite(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("kind") != "python":
        raise ValueError(f"Python-Bootstrap wird nur fuer Python-Suiten unterstuetzt: {path}")
    return payload


def _resolve_path(base_dir: Path, value: str) -> Path:
    return (base_dir / value).resolve()


def _bootstrap_python_suite(suite_path: Path, *, clean: bool) -> None:
    suite_dir = suite_path.parent
    payload = _load_suite(suite_path)
    target_dir = _resolve_path(suite_dir, str(payload.get("target_dir", ".venv")))
    runtime_dir = _resolve_path(suite_dir, str(payload["runtime_python"]))
    lockfile = _resolve_path(suite_dir, str(payload["lockfile"]))
    wheelhouses = [_resolve_path(suite_dir, str(entry)) for entry in payload.get("wheelhouses", [])]
    python_path_entries = [_resolve_path(suite_dir, str(entry)) for entry in payload.get("python_path", [])]
    bootstrap_imports = [str(entry).strip() for entry in payload.get("bootstrap_imports", []) if str(entry).strip()]

    if not lockfile.exists():
        raise FileNotFoundError(f"Lockfile fehlt: {lockfile}")
    for wheelhouse in wheelhouses:
        if not wheelhouse.exists():
            raise FileNotFoundError(f"Wheelhouse fehlt: {wheelhouse}")

    print(f"[BOOTSTRAP] {payload.get('display_name', payload.get('name', suite_dir.parent.name))}")
    print(f"  runtime: {runtime_dir}")
    print(f"  target : {target_dir}")
    copy_runtime_tree(runtime_dir, target_dir, clean=clean)
    clean_host_binding_files(target_dir)
    write_python_path_file(target_dir)
    write_python_path_overlay(target_dir, python_path_entries)

    python_exe = resolve_python_exe(target_dir)
    ensure_pip(python_exe, cwd=suite_dir)

    install_command = pip_command(
        python_exe,
        "install",
        "--no-index",
        "--upgrade",
        "--force-reinstall",
    )
    for wheelhouse in wheelhouses:
        install_command.extend(["--find-links", str(wheelhouse)])
    install_command.extend(["-r", str(lockfile)])
    run(install_command, cwd=suite_dir)
    run_import_preflight(python_exe, bootstrap_imports, cwd=suite_dir)
    print(f"[READY] {python_exe}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a module-local dev test suite from offline artifacts.")
    parser.add_argument("--suite", required=True, help="Path to dev-tests/suite.json")
    parser.add_argument("--no-clean", action="store_true", help="Reserved flag for compatibility.")
    args = parser.parse_args(argv)

    suite_path = Path(args.suite).resolve()
    if not suite_path.exists():
        raise FileNotFoundError(f"Suite-Manifest fehlt: {suite_path}")

    _bootstrap_python_suite(suite_path, clean=not args.no_clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
