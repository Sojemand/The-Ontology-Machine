"""Runtime and startup report helpers for the bundled orchestrator."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from . import adapter, workflow


def _module_root(root: str | Path | None = None) -> Path:
    return Path(root or adapter.ORCHESTRATOR_ROOT).resolve()


def _join_relative(root: Path, value: str) -> Path:
    parts = [part for part in str(value).replace("\\", "/").split("/") if part and part != "."]
    return (root.joinpath(*parts)).resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _runtime_manifest(module_root: Path) -> dict[str, Any]:
    return adapter.load_json_object(module_root / "runtime" / "runtime-manifest.json", label="runtime-manifest.json")


def _runtime_report(module_root: Path) -> dict[str, Any]:
    runtime_root = (module_root / "runtime" / "python").resolve()
    report = {
        "ok": False,
        "root_dir": str(module_root),
        "manifest_path": str(module_root / "runtime" / "runtime-manifest.json"),
        "runtime_root": str(runtime_root),
        "missing_files": [],
        "violations": [],
        "python": {
            "path": str(Path(sys.executable).resolve()),
            "version": sys.version.split()[0],
            "base_prefix": str(Path(sys.base_prefix).resolve()),
            "candidates": [],
        },
        "provenance": {
            "encodings": "",
            "tkinter": "",
            "customtkinter": "",
        },
        "error": "",
    }
    try:
        manifest = _runtime_manifest(module_root)
    except Exception as exc:
        report["error"] = str(exc)
        return report

    raw_candidates = manifest.get("runtime_candidates", {}).get("python", [])
    if not isinstance(raw_candidates, list):
        report["error"] = "runtime-manifest.json contains no valid Python candidates."
        return report
    candidates = [_join_relative(module_root, str(value)) for value in raw_candidates if str(value).strip()]
    report["python"]["candidates"] = [str(path) for path in candidates]

    raw_required = manifest.get("required_files", [])
    if not isinstance(raw_required, list):
        report["error"] = "runtime-manifest.json contains no valid required_files list."
        return report
    required_files = [_join_relative(module_root, str(value)) for value in raw_required if str(value).strip()]
    report["missing_files"] = [str(path) for path in required_files if not path.exists()]
    if report["missing_files"]:
        report["error"] = "Bundled runtime is incomplete."
        return report

    try:
        customtkinter = importlib.import_module("customtkinter")
        encodings = importlib.import_module("encodings")
        tkinter = importlib.import_module("tkinter")
    except Exception as exc:
        report["error"] = f"Bundled Python starts, but runtime imports are missing: {exc}"
        return report

    report["provenance"]["encodings"] = str(Path(encodings.__file__).resolve())
    report["provenance"]["tkinter"] = str(Path(tkinter.__file__).resolve())
    report["provenance"]["customtkinter"] = str(Path(customtkinter.__file__).resolve())

    executable = Path(report["python"]["path"])
    base_prefix = Path(report["python"]["base_prefix"])
    if candidates and executable.resolve() not in {path.resolve() for path in candidates if path.exists()}:
        report["violations"].append(f"python.exe does not match runtime-manifest.json: {executable}")
    for label, candidate in (
        ("python.path", executable),
        ("python.base_prefix", base_prefix),
        ("provenance.encodings", Path(report["provenance"]["encodings"])),
        ("provenance.tkinter", Path(report["provenance"]["tkinter"])),
        ("provenance.customtkinter", Path(report["provenance"]["customtkinter"])),
    ):
        if not _is_within(candidate, runtime_root):
            report["violations"].append(f"{label} is outside the bundled runtime: {candidate}")

    expected_version = str(manifest.get("python_version", "")).strip()
    if expected_version and not str(report["python"]["version"]).startswith(expected_version):
        report["violations"].append(
            f"Unexpected Python version: {report['python']['version']} (expected {expected_version}.x)"
        )

    if report["violations"]:
        report["error"] = "Runtime provenance is not portable."
        return report

    report["ok"] = True
    return report


def collect_runtime_report(root: str | Path | None = None) -> dict[str, Any]:
    return _runtime_report(_module_root(root))


def collect_startup_report(root: str | Path | None = None) -> dict[str, Any]:
    module_root = _module_root(root)
    runtime = _runtime_report(module_root)
    registry_path = module_root / "module-registry.json"
    federation = {
        "ok": False,
        "registry_path": str(registry_path),
        "resolved_modules": [],
        "error": "",
    }
    if runtime["ok"]:
        try:
            specs = workflow.load_module_registry(registry_path)
        except Exception as exc:
            federation["error"] = str(exc)
        else:
            federation["ok"] = True
            federation["resolved_modules"] = [
                {
                    "key": spec.key,
                    "display_name": spec.display_name,
                    "module_root": str(spec.module_root),
                    "runtime_dir": str(spec.runtime_dir),
                }
                for spec in specs.values()
            ]
    return {
        "ok": bool(runtime["ok"] and federation["ok"]),
        "root_dir": str(module_root),
        "runtime": runtime,
        "federation": federation,
        "error": federation["error"] or runtime["error"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit runtime or startup health for the Orchestrator bundle.")
    parser.add_argument("--root", default="", help="Optional module root. Defaults to the current package root.")
    parser.add_argument("--mode", choices=("runtime", "startup"), default="runtime")
    args = parser.parse_args(argv)
    report = collect_startup_report(args.root) if args.mode == "startup" else collect_runtime_report(args.root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
